#!/usr/bin/env python3
"""
Region Manager for Stock Sentiment Analysis

This module helps manage different market regions (US vs Indian markets) by:
1. Switching between regions
2. Managing region-specific stocks
3. Activating/deactivating stocks by region
4. Providing region-specific RSS feeds
"""

import argparse
import sys
from datetime import datetime
from database import DatabaseManager, Stock
from config import Config

class RegionManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = Config()
    
    def get_current_region(self):
        """Get the currently active region"""
        return self.config.DEFAULT_MARKET
    
    def list_regions(self):
        """List all available regions"""
        return {
            'US': {
                'name': 'United States',
                'description': 'US stocks (NASDAQ, NYSE)',
                'currency': 'USD',
                'exchanges': ['NASDAQ', 'NYSE']
            },
            'IN': {
                'name': 'India',
                'description': 'Indian stocks (NSE, BSE)',
                'currency': 'INR',
                'exchanges': ['NSE', 'BSE']
            }
        }
    
    def get_region_stocks(self, region):
        """Get stocks for a specific region"""
        session = self.db_manager.get_session()
        
        try:
            if region == 'US':
                # US stocks don't have .NS suffix
                stocks = session.query(Stock).filter(
                    ~Stock.symbol.contains('.NS'),
                    Stock.is_active == True
                ).all()
            elif region == 'IN':
                # Indian stocks have .NS suffix
                stocks = session.query(Stock).filter(
                    Stock.symbol.contains('.NS'),
                    Stock.is_active == True
                ).all()
            else:
                return []
            
            return stocks
        finally:
            self.db_manager.close_session(session)
    
    def get_region_rss_feeds(self, region):
        """Get RSS feeds for a specific region"""
        if region == 'US':
            return self.config.US_RSS_FEEDS
        elif region == 'IN':
            return self.config.INDIAN_RSS_FEEDS
        else:
            return []
    
    def set_active_region(self, region):
        """Set the active region by enabling only that region's stocks"""
        if region not in ['US', 'IN']:
            raise ValueError("Region must be 'US' or 'IN'")
        
        session = self.db_manager.get_session()
        
        try:
            # Get all stocks
            all_stocks = session.query(Stock).all()
            
            activated_count = 0
            deactivated_count = 0
            
            for stock in all_stocks:
                if region == 'US':
                    # Activate US stocks (no .NS suffix)
                    should_be_active = not stock.symbol.endswith('.NS')
                elif region == 'IN':
                    # Activate Indian stocks (.NS suffix)
                    should_be_active = stock.symbol.endswith('.NS')
                else:
                    should_be_active = False
                
                if should_be_active and not stock.is_active:
                    stock.is_active = True
                    activated_count += 1
                elif not should_be_active and stock.is_active:
                    stock.is_active = False
                    deactivated_count += 1
            
            session.commit()
            
            return {
                'activated': activated_count,
                'deactivated': deactivated_count,
                'region': region
            }
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.db_manager.close_session(session)
    
    def get_region_summary(self, region):
        """Get a summary of stocks in a region"""
        stocks = self.get_region_stocks(region)
        
        # Count by sector
        sector_counts = {}
        for stock in stocks:
            sector = stock.sector or 'Unknown'
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Count by market cap
        market_cap_counts = {}
        for stock in stocks:
            market_cap = stock.market_cap or 'Unknown'
            market_cap_counts[market_cap] = market_cap_counts.get(market_cap, 0) + 1
        
        return {
            'region': region,
            'total_stocks': len(stocks),
            'sectors': sector_counts,
            'market_caps': market_cap_counts,
            'rss_feeds': len(self.get_region_rss_feeds(region))
        }
    
    def show_region_status(self):
        """Show the current status of all regions"""
        regions = self.list_regions()
        
        print("=== Region Status ===")
        for region_code, region_info in regions.items():
            summary = self.get_region_summary(region_code)
            is_current = region_code == self.get_current_region()
            status = "ACTIVE" if is_current else "INACTIVE"
            
            print(f"\n{region_code} - {region_info['name']} [{status}]")
            print(f"  Description: {region_info['description']}")
            print(f"  Currency: {region_info['currency']}")
            print(f"  Active stocks: {summary['total_stocks']}")
            print(f"  RSS feeds: {summary['rss_feeds']}")
            
            if summary['sectors']:
                print(f"  Top sectors: {', '.join(list(summary['sectors'].keys())[:3])}")
            
            if is_current:
                print(f"  ✅ Currently active region")
    
    def switch_region(self, new_region):
        """Switch to a new region"""
        if new_region not in ['US', 'IN']:
            raise ValueError("Region must be 'US' or 'IN'")
        
        current_region = self.get_current_region()
        
        # Check if database stocks match config region
        us_stocks = self.get_region_stocks('US')
        in_stocks = self.get_region_stocks('IN')
        
        # Force switch if database doesn't match config
        if current_region == new_region and len(self.get_region_stocks(new_region)) > 0:
            print(f"Already using {new_region} region")
            return
        
        print(f"Switching from {current_region} to {new_region} region...")
        
        # Update active stocks
        result = self.set_active_region(new_region)
        
        print(f"✅ Region switched to {new_region}")
        print(f"  • Activated {result['activated']} stocks")
        print(f"  • Deactivated {result['deactivated']} stocks")
        
        # Update config (would need to modify config.py for persistence)
        print(f"\nNote: To make this change persistent, update DEFAULT_MARKET in config.py to '{new_region}'")
        
        return result


def main():
    """Main function for region management"""
    parser = argparse.ArgumentParser(description="Manage market regions (US vs Indian stocks)")
    parser.add_argument("--list", action="store_true", 
                       help="List all available regions")
    parser.add_argument("--status", action="store_true",
                       help="Show current region status")
    parser.add_argument("--switch", choices=['US', 'IN'],
                       help="Switch to a specific region")
    parser.add_argument("--summary", choices=['US', 'IN'],
                       help="Show summary for a specific region")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    region_manager = RegionManager()
    
    if args.list:
        regions = region_manager.list_regions()
        print("Available regions:")
        for code, info in regions.items():
            print(f"  {code}: {info['name']} - {info['description']}")
    
    if args.status:
        region_manager.show_region_status()
    
    if args.switch:
        try:
            region_manager.switch_region(args.switch)
        except Exception as e:
            print(f"Error switching region: {e}")
            sys.exit(1)
    
    if args.summary:
        summary = region_manager.get_region_summary(args.summary)
        regions = region_manager.list_regions()
        
        print(f"\n=== {args.summary} Region Summary ===")
        print(f"Region: {regions[args.summary]['name']}")
        print(f"Active stocks: {summary['total_stocks']}")
        print(f"RSS feeds: {summary['rss_feeds']}")
        
        if summary['sectors']:
            print(f"\nSectors:")
            for sector, count in summary['sectors'].items():
                print(f"  {sector}: {count} stocks")
        
        if summary['market_caps']:
            print(f"\nMarket caps:")
            for cap, count in summary['market_caps'].items():
                print(f"  {cap}: {count} stocks")


if __name__ == "__main__":
    main()
