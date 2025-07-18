#!/usr/bin/env python3
"""
Database Synchronization Manager

This module provides:
1. Automatic synchronization between SQLite and PostgreSQL databases
2. Regular sync verification to detect differences
3. Comprehensive logging for monitoring sync issues
4. Data migration and conflict resolution
"""

import sqlite3
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import hashlib
import json
import time
import schedule
import threading
from dataclasses import dataclass
from config import Config
from logger_config import get_logger

@dataclass
class SyncDiscrepancy:
    """Represents a synchronization discrepancy between databases"""
    table_name: str
    sqlite_count: int
    postgres_count: int
    difference: int
    severity: str  # 'low', 'medium', 'high'
    details: Dict

class DatabaseSyncManager:
    """Manages synchronization between SQLite and PostgreSQL databases"""
    
    def __init__(self):
        self.config = Config()
        self.logger = get_logger('database_sync_manager')
        self.sync_logger = logging.getLogger('sync_operations')
        self.error_logger = logging.getLogger('sync_errors')
        
        # Sync configuration
        self.sync_enabled = True
        self.verification_interval_minutes = 30  # Check every 30 minutes
        self.sync_batch_size = 100  # Process records in batches
        self.max_retry_attempts = 3
        
        # Track sync statistics
        self.sync_stats = {
            'last_verification': None,
            'last_sync': None,
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'discrepancies_found': 0,
            'records_synced': 0
        }
        
        self.logger.info("Database Sync Manager initialized")
    
    def get_database_connections(self) -> Tuple[sqlite3.Connection, Optional[object]]:
        """Get connections to both databases"""
        try:
            # SQLite connection
            sqlite_conn = sqlite3.connect('stock_sentiment.db')
            sqlite_conn.row_factory = sqlite3.Row  # Enable dict-like access
            
            # PostgreSQL connection
            postgres_conn = None
            try:
                postgres_conn = psycopg2.connect(
                    dbname='stock_sentiment_db',
                    user='stock_user',
                    password='StockSentiment2024!',
                    host='localhost',
                    port='5432'
                )
                postgres_conn.autocommit = False
            except Exception as e:
                self.error_logger.error(f"Failed to connect to PostgreSQL: {e}")
                
            return sqlite_conn, postgres_conn
            
        except Exception as e:
            self.error_logger.error(f"Database connection error: {e}")
            raise
    
    def verify_database_sync(self) -> List[SyncDiscrepancy]:
        """Verify synchronization between databases and return discrepancies"""
        self.logger.info("Starting database sync verification")
        discrepancies = []
        
        try:
            sqlite_conn, postgres_conn = self.get_database_connections()
            
            if not postgres_conn:
                self.error_logger.error("PostgreSQL connection not available for verification")
                return discrepancies
            
            # Tables to verify
            tables_to_verify = [
                'news_articles',
                'stock_prices', 
                'stocks',
                'company_mappings',
                'sentiment_analysis'
            ]
            
            for table in tables_to_verify:
                try:
                    discrepancy = self._verify_table_sync(sqlite_conn, postgres_conn, table)
                    if discrepancy:
                        discrepancies.append(discrepancy)
                        self.sync_logger.warning(f"Discrepancy found in {table}: {discrepancy.difference} records")
                except Exception as e:
                    self.error_logger.error(f"Error verifying table {table}: {e}")
            
            # Update statistics
            self.sync_stats['last_verification'] = datetime.now()
            self.sync_stats['discrepancies_found'] += len(discrepancies)
            
            if discrepancies:
                self.sync_logger.warning(f"Found {len(discrepancies)} discrepancies during verification")
            else:
                self.sync_logger.info("No discrepancies found - databases are in sync")
                
        except Exception as e:
            self.error_logger.error(f"Sync verification failed: {e}")
            
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if postgres_conn:
                postgres_conn.close()
        
        return discrepancies
    
    def _verify_table_sync(self, sqlite_conn: sqlite3.Connection, 
                          postgres_conn: object, 
                          table_name: str) -> Optional[SyncDiscrepancy]:
        """Verify synchronization for a specific table"""
        try:
            # Get record counts
            sqlite_count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table_name}", sqlite_conn)['count'][0]
            postgres_count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table_name}", postgres_conn)['count'][0]
            
            difference = abs(sqlite_count - postgres_count)
            
            if difference > 0:
                # Determine severity
                if difference <= 5:
                    severity = 'low'
                elif difference <= 20:
                    severity = 'medium'
                else:
                    severity = 'high'
                
                # Get additional details
                details = self._get_table_sync_details(sqlite_conn, postgres_conn, table_name)
                
                return SyncDiscrepancy(
                    table_name=table_name,
                    sqlite_count=sqlite_count,
                    postgres_count=postgres_count,
                    difference=difference,
                    severity=severity,
                    details=details
                )
            
            return None
            
        except Exception as e:
            self.error_logger.error(f"Error verifying table {table_name}: {e}")
            return None
    
    def _get_table_sync_details(self, sqlite_conn: sqlite3.Connection, 
                               postgres_conn: object, 
                               table_name: str) -> Dict:
        """Get detailed information about table synchronization issues"""
        details = {}
        
        try:
            # Get recent records from both databases
            if table_name == 'news_articles':
                sqlite_recent = pd.read_sql_query(
                    "SELECT url, title, created_at FROM news_articles ORDER BY created_at DESC LIMIT 10",
                    sqlite_conn
                )
                postgres_recent = pd.read_sql_query(
                    "SELECT url, title, created_at FROM news_articles ORDER BY created_at DESC LIMIT 10",
                    postgres_conn
                )
                
                # Find URLs that exist in one but not the other
                sqlite_urls = set(sqlite_recent['url'].tolist())
                postgres_urls = set(postgres_recent['url'].tolist())
                
                details['sqlite_only_urls'] = list(sqlite_urls - postgres_urls)
                details['postgres_only_urls'] = list(postgres_urls - sqlite_urls)
                
            elif table_name == 'stocks':
                sqlite_stocks = pd.read_sql_query("SELECT symbol, is_active FROM stocks", sqlite_conn)
                postgres_stocks = pd.read_sql_query("SELECT symbol, is_active FROM stocks", postgres_conn)
                
                details['sqlite_active_count'] = len(sqlite_stocks[sqlite_stocks['is_active'] == 1])
                details['postgres_active_count'] = len(postgres_stocks[postgres_stocks['is_active'] == True])
                
        except Exception as e:
            self.error_logger.error(f"Error getting sync details for {table_name}: {e}")
            details['error'] = str(e)
        
        return details
    
    def synchronize_databases(self, discrepancies: List[SyncDiscrepancy] = None) -> bool:
        """Synchronize databases based on discrepancies or full sync"""
        self.logger.info("Starting database synchronization")
        
        try:
            if discrepancies is None:
                discrepancies = self.verify_database_sync()
            
            if not discrepancies:
                self.sync_logger.info("No discrepancies found, skipping synchronization")
                return True
            
            sqlite_conn, postgres_conn = self.get_database_connections()
            
            if not postgres_conn:
                self.error_logger.error("PostgreSQL connection not available for synchronization")
                return False
            
            success = True
            synced_records = 0
            
            for discrepancy in discrepancies:
                try:
                    records_synced = self._synchronize_table(
                        sqlite_conn, postgres_conn, discrepancy
                    )
                    synced_records += records_synced
                    self.sync_logger.info(f"Synchronized {records_synced} records for table {discrepancy.table_name}")
                    
                except Exception as e:
                    self.error_logger.error(f"Failed to sync table {discrepancy.table_name}: {e}")
                    success = False
            
            # Update statistics
            self.sync_stats['last_sync'] = datetime.now()
            self.sync_stats['total_syncs'] += 1
            self.sync_stats['records_synced'] += synced_records
            
            if success:
                self.sync_stats['successful_syncs'] += 1
                self.sync_logger.info(f"Database synchronization completed successfully. Synced {synced_records} records")
            else:
                self.sync_stats['failed_syncs'] += 1
                self.sync_logger.error("Database synchronization completed with errors")
            
            return success
            
        except Exception as e:
            self.error_logger.error(f"Database synchronization failed: {e}")
            self.sync_stats['failed_syncs'] += 1
            return False
        
        finally:
            if sqlite_conn:
                sqlite_conn.close()
            if postgres_conn:
                postgres_conn.close()
    
    def _synchronize_table(self, sqlite_conn: sqlite3.Connection,
                          postgres_conn: object,
                          discrepancy: SyncDiscrepancy) -> int:
        """Synchronize a specific table based on discrepancy"""
        table_name = discrepancy.table_name
        records_synced = 0
        
        try:
            # Determine sync direction (from larger to smaller database)
            if discrepancy.sqlite_count > discrepancy.postgres_count:
                # Sync from SQLite to PostgreSQL
                records_synced = self._sync_sqlite_to_postgres(
                    sqlite_conn, postgres_conn, table_name
                )
            else:
                # Sync from PostgreSQL to SQLite
                records_synced = self._sync_postgres_to_sqlite(
                    sqlite_conn, postgres_conn, table_name
                )
                
        except Exception as e:
            self.error_logger.error(f"Error synchronizing table {table_name}: {e}")
            raise
        
        return records_synced
    
    def _sync_sqlite_to_postgres(self, sqlite_conn: sqlite3.Connection,
                                postgres_conn: object,
                                table_name: str) -> int:
        """Sync records from SQLite to PostgreSQL"""
        records_synced = 0
        
        try:
            # Get records from SQLite that don't exist in PostgreSQL
            if table_name == 'news_articles':
                # Get SQLite URLs
                sqlite_urls = pd.read_sql_query("SELECT url FROM news_articles", sqlite_conn)['url'].tolist()
                
                # Get PostgreSQL URLs
                postgres_urls = pd.read_sql_query("SELECT url FROM news_articles", postgres_conn)['url'].tolist()
                
                # Find missing URLs
                missing_urls = list(set(sqlite_urls) - set(postgres_urls))
                
                if missing_urls:
                    # Get full records for missing URLs
                    placeholders = ','.join(['?' for _ in missing_urls])
                    query = f"SELECT * FROM news_articles WHERE url IN ({placeholders})"
                    missing_records = pd.read_sql_query(query, sqlite_conn, params=missing_urls)
                    
                    # Insert into PostgreSQL
                    records_synced = self._insert_records_to_postgres(
                        postgres_conn, table_name, missing_records
                    )
                    
            elif table_name == 'stocks':
                # Sync stock records
                sqlite_stocks = pd.read_sql_query("SELECT * FROM stocks", sqlite_conn)
                postgres_stocks = pd.read_sql_query("SELECT * FROM stocks", postgres_conn)
                
                # Find stocks that exist in SQLite but not in PostgreSQL
                sqlite_symbols = set(sqlite_stocks['symbol'].tolist())
                postgres_symbols = set(postgres_stocks['symbol'].tolist())
                missing_symbols = list(sqlite_symbols - postgres_symbols)
                
                if missing_symbols:
                    missing_records = sqlite_stocks[sqlite_stocks['symbol'].isin(missing_symbols)]
                    records_synced = self._insert_records_to_postgres(
                        postgres_conn, table_name, missing_records
                    )
                    
            elif table_name == 'company_mappings':
                # Sync company mappings
                sqlite_mappings = pd.read_sql_query("SELECT * FROM company_mappings", sqlite_conn)
                postgres_mappings = pd.read_sql_query("SELECT * FROM company_mappings", postgres_conn)
                
                # Find mappings that exist in SQLite but not in PostgreSQL
                sqlite_keys = set(sqlite_mappings.apply(lambda x: f"{x['company_name']}_{x['stock_symbol']}", axis=1).tolist())
                postgres_keys = set(postgres_mappings.apply(lambda x: f"{x['company_name']}_{x['stock_symbol']}", axis=1).tolist())
                missing_keys = list(sqlite_keys - postgres_keys)
                
                if missing_keys:
                    missing_records = sqlite_mappings[sqlite_mappings.apply(lambda x: f"{x['company_name']}_{x['stock_symbol']}", axis=1).isin(missing_keys)]
                    records_synced = self._insert_records_to_postgres(
                        postgres_conn, table_name, missing_records
                    )
                    
            elif table_name == 'stock_prices':
                # Sync stock prices (only recent ones to avoid massive data transfer)
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=7)
                
                sqlite_prices = pd.read_sql_query("SELECT * FROM stock_prices WHERE timestamp >= ?", sqlite_conn, params=[cutoff_date])
                postgres_prices = pd.read_sql_query("SELECT * FROM stock_prices WHERE timestamp >= %s", postgres_conn, params=[cutoff_date])
                
                # Find prices that exist in SQLite but not in PostgreSQL
                sqlite_keys = set(sqlite_prices.apply(lambda x: f"{x['symbol']}_{x['timestamp']}", axis=1).tolist())
                postgres_keys = set(postgres_prices.apply(lambda x: f"{x['symbol']}_{x['timestamp']}", axis=1).tolist())
                missing_keys = list(sqlite_keys - postgres_keys)
                
                if missing_keys:
                    missing_records = sqlite_prices[sqlite_prices.apply(lambda x: f"{x['symbol']}_{x['timestamp']}", axis=1).isin(missing_keys)]
                    records_synced = self._insert_records_to_postgres(
                        postgres_conn, table_name, missing_records
                    )
                    
            elif table_name == 'sentiment_analysis':
                # Sync sentiment analysis
                sqlite_sentiment = pd.read_sql_query("SELECT * FROM sentiment_analysis", sqlite_conn)
                postgres_sentiment = pd.read_sql_query("SELECT * FROM sentiment_analysis", postgres_conn)
                
                # Find sentiment records that exist in SQLite but not in PostgreSQL
                sqlite_keys = set(sqlite_sentiment.apply(lambda x: f"{x['symbol']}_{x['date']}", axis=1).tolist())
                postgres_keys = set(postgres_sentiment.apply(lambda x: f"{x['symbol']}_{x['date']}", axis=1).tolist())
                missing_keys = list(sqlite_keys - postgres_keys)
                
                if missing_keys:
                    missing_records = sqlite_sentiment[sqlite_sentiment.apply(lambda x: f"{x['symbol']}_{x['date']}", axis=1).isin(missing_keys)]
                    records_synced = self._insert_records_to_postgres(
                        postgres_conn, table_name, missing_records
                    )
                    
        except Exception as e:
            self.error_logger.error(f"Error syncing {table_name} from SQLite to PostgreSQL: {e}")
            raise
        
        return records_synced
    
    def _sync_postgres_to_sqlite(self, sqlite_conn: sqlite3.Connection,
                                postgres_conn: object,
                                table_name: str) -> int:
        """Sync records from PostgreSQL to SQLite"""
        records_synced = 0
        
        try:
            # Similar logic but in reverse direction
            if table_name == 'news_articles':
                # Get PostgreSQL URLs
                postgres_urls = pd.read_sql_query("SELECT url FROM news_articles", postgres_conn)['url'].tolist()
                
                # Get SQLite URLs
                sqlite_urls = pd.read_sql_query("SELECT url FROM news_articles", sqlite_conn)['url'].tolist()
                
                # Find missing URLs
                missing_urls = list(set(postgres_urls) - set(sqlite_urls))
                
                if missing_urls:
                    # Get full records for missing URLs
                    placeholders = ','.join(['%s' for _ in missing_urls])
                    query = f"SELECT * FROM news_articles WHERE url IN ({placeholders})"
                    missing_records = pd.read_sql_query(query, postgres_conn, params=missing_urls)
                    
                    # Insert into SQLite
                    records_synced = self._insert_records_to_sqlite(
                        sqlite_conn, table_name, missing_records
                    )
                    
        except Exception as e:
            self.error_logger.error(f"Error syncing {table_name} from PostgreSQL to SQLite: {e}")
            raise
        
        return records_synced
    
    def _insert_records_to_postgres(self, postgres_conn: object,
                                   table_name: str, records: pd.DataFrame) -> int:
        """Insert records into PostgreSQL database"""
        if records.empty:
            return 0
        
        try:
            cursor = postgres_conn.cursor()
            records_inserted = 0
            
            for _, record in records.iterrows():
                try:
                    if table_name == 'news_articles':
                        cursor.execute("""
                            INSERT INTO news_articles (title, content, url, source, published_date, 
                                                     stock_symbol, sentiment_score, sentiment_label,
                                                     vader_score, textblob_score, finbert_score, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (url) DO NOTHING
                        """, (
                            record['title'], record['content'], record['url'], record['source'],
                            record['published_date'], record['stock_symbol'], record['sentiment_score'],
                            record['sentiment_label'], record['vader_score'], record['textblob_score'],
                            record['finbert_score'], record['created_at']
                        ))
                    
                    elif table_name == 'stocks':
                        cursor.execute("""
                            INSERT INTO stocks (symbol, company_name, sector, industry, market_cap, 
                                              is_active, is_etf, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol) DO UPDATE SET
                                company_name = EXCLUDED.company_name,
                                is_active = EXCLUDED.is_active,
                                updated_at = EXCLUDED.updated_at
                        """, (
                            record['symbol'], record['company_name'], record['sector'],
                            record['industry'], record['market_cap'], record['is_active'],
                            record['is_etf'], record['created_at'], record['updated_at']
                        ))
                    
                    elif table_name == 'company_mappings':
                        cursor.execute("""
                            INSERT INTO company_mappings (company_name, stock_symbol, is_active, created_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (company_name, stock_symbol) DO UPDATE SET
                                is_active = EXCLUDED.is_active
                        """, (
                            record['company_name'], record['stock_symbol'], record['is_active'], record['created_at']
                        ))
                    
                    elif table_name == 'stock_prices':
                        cursor.execute("""
                            INSERT INTO stock_prices (symbol, price, volume, timestamp, open_price, high_price, low_price, close_price)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, timestamp) DO NOTHING
                        """, (
                            record['symbol'], record['price'], record['volume'], record['timestamp'],
                            record['open_price'], record['high_price'], record['low_price'], record['close_price']
                        ))
                    
                    elif table_name == 'sentiment_analysis':
                        cursor.execute("""
                            INSERT INTO sentiment_analysis (symbol, date, avg_sentiment, sentiment_count, 
                                                          positive_count, negative_count, neutral_count, news_sentiment)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, date) DO UPDATE SET
                                avg_sentiment = EXCLUDED.avg_sentiment,
                                sentiment_count = EXCLUDED.sentiment_count,
                                positive_count = EXCLUDED.positive_count,
                                negative_count = EXCLUDED.negative_count,
                                neutral_count = EXCLUDED.neutral_count,
                                news_sentiment = EXCLUDED.news_sentiment
                        """, (
                            record['symbol'], record['date'], record['avg_sentiment'], record['sentiment_count'],
                            record['positive_count'], record['negative_count'], record['neutral_count'], record['news_sentiment']
                        ))
                    
                    records_inserted += 1
                    
                except Exception as e:
                    self.error_logger.error(f"Error inserting record into PostgreSQL: {e}")
                    continue
            
            postgres_conn.commit()
            return records_inserted
            
        except Exception as e:
            postgres_conn.rollback()
            self.error_logger.error(f"Error inserting records to PostgreSQL: {e}")
            raise
    
    def _insert_records_to_sqlite(self, sqlite_conn: sqlite3.Connection,
                                 table_name: str, records: pd.DataFrame) -> int:
        """Insert records into SQLite database"""
        if records.empty:
            return 0
        
        try:
            cursor = sqlite_conn.cursor()
            records_inserted = 0
            
            for _, record in records.iterrows():
                try:
                    if table_name == 'news_articles':
                        cursor.execute("""
                            INSERT OR IGNORE INTO news_articles (title, content, url, source, published_date, 
                                                               stock_symbol, sentiment_score, sentiment_label,
                                                               vader_score, textblob_score, finbert_score, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record['title'], record['content'], record['url'], record['source'],
                            record['published_date'], record['stock_symbol'], record['sentiment_score'],
                            record['sentiment_label'], record['vader_score'], record['textblob_score'],
                            record['finbert_score'], record['created_at']
                        ))
                    
                    elif table_name == 'stocks':
                        cursor.execute("""
                            INSERT OR REPLACE INTO stocks (symbol, company_name, sector, industry, market_cap, 
                                                         is_active, is_etf, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record['symbol'], record['company_name'], record['sector'],
                            record['industry'], record['market_cap'], record['is_active'],
                            record['is_etf'], record['created_at'], record['updated_at']
                        ))
                    
                    records_inserted += 1
                    
                except Exception as e:
                    self.error_logger.error(f"Error inserting record into SQLite: {e}")
                    continue
            
            sqlite_conn.commit()
            return records_inserted
            
        except Exception as e:
            sqlite_conn.rollback()
            self.error_logger.error(f"Error inserting records to SQLite: {e}")
            raise
    
    def get_sync_status(self) -> Dict:
        """Get current synchronization status"""
        return {
            'sync_enabled': self.sync_enabled,
            'verification_interval_minutes': self.verification_interval_minutes,
            'statistics': self.sync_stats.copy(),
            'last_verification_age_minutes': (
                (datetime.now() - self.sync_stats['last_verification']).total_seconds() / 60
                if self.sync_stats['last_verification'] else None
            )
        }
    
    def start_automatic_sync(self):
        """Start automatic synchronization verification"""
        self.logger.info(f"Starting automatic sync verification every {self.verification_interval_minutes} minutes")
        
        # Schedule verification
        schedule.every(self.verification_interval_minutes).minutes.do(self._run_verification_cycle)
        
        # Run scheduler in a separate thread
        def run_scheduler():
            while self.sync_enabled:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Run initial verification
        self._run_verification_cycle()
    
    def _run_verification_cycle(self):
        """Run a complete verification and sync cycle"""
        try:
            self.sync_logger.info("Starting scheduled verification cycle")
            
            # Verify databases
            discrepancies = self.verify_database_sync()
            
            # If discrepancies found, run synchronization
            if discrepancies:
                self.sync_logger.warning(f"Found {len(discrepancies)} discrepancies, starting synchronization")
                self.synchronize_databases(discrepancies)
            
            # Log status
            status = self.get_sync_status()
            self.sync_logger.info(f"Verification cycle completed. Status: {status}")
            
        except Exception as e:
            self.error_logger.error(f"Verification cycle failed: {e}")
    
    def stop_automatic_sync(self):
        """Stop automatic synchronization"""
        self.sync_enabled = False
        schedule.clear()
        self.logger.info("Automatic sync stopped")

# Standalone sync verification script
def main():
    """Main function for standalone sync verification"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Synchronization Manager")
    parser.add_argument("--verify", action="store_true", help="Verify database synchronization")
    parser.add_argument("--sync", action="store_true", help="Synchronize databases")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--auto", action="store_true", help="Start automatic sync monitoring")
    
    args = parser.parse_args()
    
    sync_manager = DatabaseSyncManager()
    
    if args.verify:
        discrepancies = sync_manager.verify_database_sync()
        print(f"Found {len(discrepancies)} discrepancies")
        for d in discrepancies:
            print(f"  {d.table_name}: {d.difference} records difference ({d.severity} severity)")
    
    elif args.sync:
        success = sync_manager.synchronize_databases()
        print(f"Synchronization {'successful' if success else 'failed'}")
    
    elif args.status:
        status = sync_manager.get_sync_status()
        print(f"Sync Status: {json.dumps(status, indent=2, default=str)}")
    
    elif args.auto:
        print("Starting automatic sync monitoring...")
        sync_manager.start_automatic_sync()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping automatic sync...")
            sync_manager.stop_automatic_sync()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
