from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError
from datetime import datetime
from config import Config
import sys

Base = declarative_base()

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    url = Column(String(1000), unique=True)
    source = Column(String(100))
    published_date = Column(DateTime)
    stock_symbol = Column(String(20))  # Increased for Indian stocks
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))
    vader_score = Column(Float)
    textblob_score = Column(Float)
    finbert_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockPrice(Base):
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)  # Increased for Indian stocks like RELIANCE.NS
    price = Column(Float, nullable=False)
    volume = Column(Integer)
    timestamp = Column(DateTime, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)

class Stock(Base):
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True)  # Increased for Indian stocks
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(String(20))  # Small, Mid, Large
    is_active = Column(Boolean, default=True)
    is_etf = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CompanyMapping(Base):
    __tablename__ = 'company_mappings'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(200), nullable=False)
    stock_symbol = Column(String(20), nullable=False)  # Increased for Indian stocks
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SentimentAnalysis(Base):
    __tablename__ = 'sentiment_analysis'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)  # Increased for Indian stocks
    date = Column(DateTime, nullable=False)
    avg_sentiment = Column(Float)
    sentiment_count = Column(Integer)
    positive_count = Column(Integer)
    negative_count = Column(Integer)
    neutral_count = Column(Integer)
    news_sentiment = Column(Float)

class DatabaseManager:
    def __init__(self):
        try:
            # Check if password is set when using PostgreSQL
            if Config.DB_TYPE == 'postgresql' and not Config.DB_PASSWORD:
                raise ValueError("DB_PASSWORD is not set in .env file")
            
            self.engine = create_engine(Config.DATABASE_URL)
            # Test the connection
            self._test_connection()
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(bind=self.engine)
        except Exception as e:
            self._handle_database_error(e)
    
    def _test_connection(self):
        """Test database connection"""
        try:
            # Try to connect to the database
            with self.engine.connect() as connection:
                pass
        except Exception as e:
            raise e
    
    def _handle_database_error(self, error):
        """Handle database connection errors with user-friendly messages"""
        error_message = str(error).lower()
        
        # Check for missing password error first
        if 'db_password is not set in .env file' in error_message:
            print("\n❌ PostgreSQL Configuration Error:")
            print("   DB_PASSWORD is not set in your .env file.")
            print("   \n📝 Current PostgreSQL configuration:")
            print(f"   - Host: {Config.DB_HOST}")
            print(f"   - Port: {Config.DB_PORT}")
            print(f"   - Database: {Config.DB_NAME}")
            print(f"   - User: {Config.DB_USER}")
            print("   - Password: [NOT SET - Check your .env file]")
            print("   \n💡 To fix this:")
            print("   1. Open your .env file")
            print("   2. Uncomment the PostgreSQL configuration lines")
            print("   3. Set DB_PASSWORD=your_actual_password")
            print("   4. Or switch to SQLite by setting DB_TYPE=sqlite")
        
        # Check for PostgreSQL-specific errors
        elif 'postgresql' in Config.DATABASE_URL.lower():
            if 'password authentication failed' in error_message or 'no password supplied' in error_message:
                print("\n❌ PostgreSQL Authentication Error:")
                print("   Please check your PostgreSQL credentials in the .env file.")
                print("   Make sure DB_PASSWORD is set correctly.")
                print("   \n📝 Current PostgreSQL configuration:")
                print(f"   - Host: {Config.DB_HOST}")
                print(f"   - Port: {Config.DB_PORT}")
                print(f"   - Database: {Config.DB_NAME}")
                print(f"   - User: {Config.DB_USER}")
                print("   - Password: [Check your .env file]")
                print("   \n💡 To fix this:")
                print("   1. Open your .env file")
                print("   2. Set DB_PASSWORD=your_actual_password")
                print("   3. Or switch to SQLite by setting DB_TYPE=sqlite")
                
            elif 'could not connect to server' in error_message or 'connection refused' in error_message:
                print("\n❌ PostgreSQL Connection Error:")
                print("   Cannot connect to PostgreSQL server.")
                print("   Please make sure PostgreSQL is running and accessible.")
                print("   \n💡 To fix this:")
                print("   1. Start your PostgreSQL service")
                print("   2. Check if the connection details are correct")
                print("   3. Or switch to SQLite by setting DB_TYPE=sqlite in .env")
                
            elif 'database' in error_message and 'does not exist' in error_message:
                print("\n❌ PostgreSQL Database Error:")
                print(f"   Database '{Config.DB_NAME}' does not exist.")
                print("   Please create the database first.")
                print("   \n💡 To fix this:")
                print("   1. Create the database in PostgreSQL")
                print("   2. Or run the setup script to create it automatically")
                print("   3. Or switch to SQLite by setting DB_TYPE=sqlite in .env")
            else:
                print("\n❌ PostgreSQL Error:")
                print(f"   {error}")
                print("   \n💡 Consider switching to SQLite for easier setup:")
                print("   Set DB_TYPE=sqlite in your .env file")
        else:
            # SQLite or other database errors
            print("\n❌ Database Error:")
            print(f"   {error}")
        
        print("\n🔄 For immediate testing, you can:")
        print("   1. Use SQLite (no password required): Set DB_TYPE=sqlite")
        print("   2. Check the .env.template file for configuration examples")
        print("\nExiting...")
        sys.exit(1)
    
    def get_session(self):
        return self.SessionLocal()
    
    def close_session(self, session):
        session.close()
    
    def save_news_article(self, article_data):
        session = self.get_session()
        try:
            # Simple save like SQLite - let database constraints handle duplicates
            article = NewsArticle(**article_data)
            session.add(article)
            session.commit()
            return article.id
        except Exception as e:
            session.rollback()
            # Check if it's a duplicate URL error and handle gracefully
            error_str = str(e).lower()
            if 'duplicate' in error_str or 'unique constraint' in error_str:
                # Silently handle duplicate - this is expected behavior
                return None
            else:
                print(f"Error saving news article: {e}")
                return None
        finally:
            self.close_session(session)
    
    def save_stock_price(self, price_data):
        session = self.get_session()
        try:
            stock_price = StockPrice(**price_data)
            session.add(stock_price)
            session.commit()
            return stock_price.id
        except Exception as e:
            session.rollback()
            print(f"Error saving stock price: {e}")
            return None
        finally:
            self.close_session(session)
    
    def get_recent_sentiment(self, symbol, days=7):
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            results = session.query(SentimentAnalysis).filter(
                SentimentAnalysis.symbol == symbol,
                SentimentAnalysis.date >= cutoff_date
            ).order_by(SentimentAnalysis.date.desc()).all()
            
            return results
        finally:
            self.close_session(session)
    
    def get_active_stocks(self):
        """Get all active stock symbols"""
        session = self.get_session()
        try:
            stocks = session.query(Stock).filter(Stock.is_active == True).all()
            return [stock.symbol for stock in stocks]
        finally:
            self.close_session(session)
    
    def get_company_mappings(self):
        """Get all active company name to symbol mappings"""
        session = self.get_session()
        try:
            mappings = session.query(CompanyMapping).filter(CompanyMapping.is_active == True).all()
            return {mapping.company_name.upper(): mapping.stock_symbol for mapping in mappings}
        finally:
            self.close_session(session)
    
    def add_stock(self, symbol, company_name, sector=None, industry=None, market_cap=None, is_etf=False):
        """Add a new stock to track"""
        session = self.get_session()
        try:
            # Check if stock already exists
            existing = session.query(Stock).filter(Stock.symbol == symbol).first()
            if existing:
                existing.is_active = True
                existing.company_name = company_name
                existing.sector = sector
                existing.industry = industry
                existing.market_cap = market_cap
                existing.is_etf = is_etf
                existing.updated_at = datetime.utcnow()
            else:
                stock = Stock(
                    symbol=symbol,
                    company_name=company_name,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap,
                    is_etf=is_etf
                )
                session.add(stock)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error adding stock {symbol}: {e}")
            return False
        finally:
            self.close_session(session)
    
    def add_company_mapping(self, company_name, stock_symbol):
        """Add a company name to stock symbol mapping"""
        session = self.get_session()
        try:
            # Check if mapping already exists
            existing = session.query(CompanyMapping).filter(
                CompanyMapping.company_name == company_name,
                CompanyMapping.stock_symbol == stock_symbol
            ).first()
            
            if existing:
                existing.is_active = True
            else:
                mapping = CompanyMapping(
                    company_name=company_name,
                    stock_symbol=stock_symbol
                )
                session.add(mapping)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error adding company mapping {company_name} -> {stock_symbol}: {e}")
            return False
        finally:
            self.close_session(session)
    
    def deactivate_stock(self, symbol):
        """Deactivate a stock (stop tracking it)"""
        session = self.get_session()
        try:
            stock = session.query(Stock).filter(Stock.symbol == symbol).first()
            if stock:
                stock.is_active = False
                stock.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error deactivating stock {symbol}: {e}")
            return False
        finally:
            self.close_session(session)
    
    def bulk_insert_stocks(self, stocks_data):
        """Bulk insert stocks data"""
        session = self.get_session()
        try:
            for stock_data in stocks_data:
                existing = session.query(Stock).filter(Stock.symbol == stock_data['symbol']).first()
                if not existing:
                    stock = Stock(**stock_data)
                    session.add(stock)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error bulk inserting stocks: {e}")
            return False
        finally:
            self.close_session(session)
    
    def bulk_insert_company_mappings(self, mappings_data):
        """Bulk insert company mappings data"""
        session = self.get_session()
        try:
            for mapping_data in mappings_data:
                existing = session.query(CompanyMapping).filter(
                    CompanyMapping.company_name == mapping_data['company_name'],
                    CompanyMapping.stock_symbol == mapping_data['stock_symbol']
                ).first()
                if not existing:
                    mapping = CompanyMapping(**mapping_data)
                    session.add(mapping)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error bulk inserting company mappings: {e}")
            return False
        finally:
            self.close_session(session)
    
    def initialize_default_data(self):
        """Initialize database with default stocks and company mappings"""
        print("🚀 Initializing default data...")
        print("📈 Originally built for Indian market, recently expanded to US market")
        
        # Indian stocks (original market focus) - using NSE symbols but Yahoo Finance format
        indian_stocks = [
            {'symbol': 'RELIANCE.NS', 'company_name': 'Reliance Industries Limited', 'sector': 'Energy', 'industry': 'Oil & Gas', 'market_cap': 'Large'},
            {'symbol': 'TCS.NS', 'company_name': 'Tata Consultancy Services', 'sector': 'Technology', 'industry': 'IT Services', 'market_cap': 'Large'},
            {'symbol': 'HDFCBANK.NS', 'company_name': 'HDFC Bank Limited', 'sector': 'Financial Services', 'industry': 'Banking', 'market_cap': 'Large'},
            {'symbol': 'INFY.NS', 'company_name': 'Infosys Limited', 'sector': 'Technology', 'industry': 'IT Services', 'market_cap': 'Large'},
            {'symbol': 'HINDUNILVR.NS', 'company_name': 'Hindustan Unilever Limited', 'sector': 'Consumer Goods', 'industry': 'FMCG', 'market_cap': 'Large'},
            {'symbol': 'ICICIBANK.NS', 'company_name': 'ICICI Bank Limited', 'sector': 'Financial Services', 'industry': 'Banking', 'market_cap': 'Large'},
            {'symbol': 'BHARTIARTL.NS', 'company_name': 'Bharti Airtel Limited', 'sector': 'Communication Services', 'industry': 'Telecommunications', 'market_cap': 'Large'},
            {'symbol': 'ITC.NS', 'company_name': 'ITC Limited', 'sector': 'Consumer Goods', 'industry': 'Tobacco & FMCG', 'market_cap': 'Large'},
            {'symbol': 'SBIN.NS', 'company_name': 'State Bank of India', 'sector': 'Financial Services', 'industry': 'Banking', 'market_cap': 'Large'},
            {'symbol': 'KOTAKBANK.NS', 'company_name': 'Kotak Mahindra Bank', 'sector': 'Financial Services', 'industry': 'Banking', 'market_cap': 'Large'},
            {'symbol': 'LT.NS', 'company_name': 'Larsen & Toubro Limited', 'sector': 'Industrials', 'industry': 'Engineering & Construction', 'market_cap': 'Large'},
            {'symbol': 'HCLTECH.NS', 'company_name': 'HCL Technologies Limited', 'sector': 'Technology', 'industry': 'IT Services', 'market_cap': 'Large'},
            {'symbol': 'MARUTI.NS', 'company_name': 'Maruti Suzuki India Limited', 'sector': 'Consumer Discretionary', 'industry': 'Automobiles', 'market_cap': 'Large'},
            {'symbol': 'ASIANPAINT.NS', 'company_name': 'Asian Paints Limited', 'sector': 'Materials', 'industry': 'Paints & Coatings', 'market_cap': 'Large'},
            {'symbol': 'TITAN.NS', 'company_name': 'Titan Company Limited', 'sector': 'Consumer Discretionary', 'industry': 'Jewelry & Watches', 'market_cap': 'Large'},
        ]
        
        # US stocks (recently added for expansion)
        us_stocks = [
            {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'sector': 'Technology', 'industry': 'Consumer Electronics', 'market_cap': 'Large'},
            {'symbol': 'GOOGL', 'company_name': 'Alphabet Inc.', 'sector': 'Technology', 'industry': 'Internet Services', 'market_cap': 'Large'},
            {'symbol': 'MSFT', 'company_name': 'Microsoft Corporation', 'sector': 'Technology', 'industry': 'Software', 'market_cap': 'Large'},
            {'symbol': 'AMZN', 'company_name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary', 'industry': 'E-commerce', 'market_cap': 'Large'},
            {'symbol': 'TSLA', 'company_name': 'Tesla Inc.', 'sector': 'Consumer Discretionary', 'industry': 'Electric Vehicles', 'market_cap': 'Large'},
            {'symbol': 'META', 'company_name': 'Meta Platforms Inc.', 'sector': 'Technology', 'industry': 'Social Media', 'market_cap': 'Large'},
            {'symbol': 'NFLX', 'company_name': 'Netflix Inc.', 'sector': 'Communication Services', 'industry': 'Streaming', 'market_cap': 'Large'},
            {'symbol': 'NVDA', 'company_name': 'NVIDIA Corporation', 'sector': 'Technology', 'industry': 'Semiconductors', 'market_cap': 'Large'},
            {'symbol': 'SPY', 'company_name': 'SPDR S&P 500 ETF Trust', 'sector': 'Financial Services', 'industry': 'Exchange Traded Fund', 'market_cap': 'Large', 'is_etf': True},
            {'symbol': 'QQQ', 'company_name': 'Invesco QQQ Trust', 'sector': 'Financial Services', 'industry': 'Exchange Traded Fund', 'market_cap': 'Large', 'is_etf': True},
        ]
        
        # Combine stocks - Indian first (original focus), then US (recent addition)
        default_stocks = indian_stocks + us_stocks
        
        # Default company name mappings - Indian companies (original focus) + US companies (recent addition)
        indian_mappings = [
            # Reliance Industries
            {'company_name': 'Reliance', 'stock_symbol': 'RELIANCE.NS'},
            {'company_name': 'Reliance Industries', 'stock_symbol': 'RELIANCE.NS'},
            {'company_name': 'RIL', 'stock_symbol': 'RELIANCE.NS'},
            # TCS
            {'company_name': 'TCS', 'stock_symbol': 'TCS.NS'},
            {'company_name': 'Tata Consultancy Services', 'stock_symbol': 'TCS.NS'},
            {'company_name': 'Tata Consultancy', 'stock_symbol': 'TCS.NS'},
            # HDFC Bank
            {'company_name': 'HDFC Bank', 'stock_symbol': 'HDFCBANK.NS'},
            {'company_name': 'HDFC', 'stock_symbol': 'HDFCBANK.NS'},
            # Infosys
            {'company_name': 'Infosys', 'stock_symbol': 'INFY.NS'},
            {'company_name': 'Infy', 'stock_symbol': 'INFY.NS'},
            # Hindustan Unilever
            {'company_name': 'Hindustan Unilever', 'stock_symbol': 'HINDUNILVR.NS'},
            {'company_name': 'HUL', 'stock_symbol': 'HINDUNILVR.NS'},
            # ICICI Bank
            {'company_name': 'ICICI Bank', 'stock_symbol': 'ICICIBANK.NS'},
            {'company_name': 'ICICI', 'stock_symbol': 'ICICIBANK.NS'},
            # Bharti Airtel
            {'company_name': 'Bharti Airtel', 'stock_symbol': 'BHARTIARTL.NS'},
            {'company_name': 'Airtel', 'stock_symbol': 'BHARTIARTL.NS'},
            # ITC
            {'company_name': 'ITC', 'stock_symbol': 'ITC.NS'},
            {'company_name': 'ITC Limited', 'stock_symbol': 'ITC.NS'},
            # State Bank of India
            {'company_name': 'State Bank of India', 'stock_symbol': 'SBIN.NS'},
            {'company_name': 'SBI', 'stock_symbol': 'SBIN.NS'},
            # Kotak Mahindra Bank
            {'company_name': 'Kotak Mahindra Bank', 'stock_symbol': 'KOTAKBANK.NS'},
            {'company_name': 'Kotak Bank', 'stock_symbol': 'KOTAKBANK.NS'},
            {'company_name': 'Kotak', 'stock_symbol': 'KOTAKBANK.NS'},
            # L&T
            {'company_name': 'Larsen & Toubro', 'stock_symbol': 'LT.NS'},
            {'company_name': 'L&T', 'stock_symbol': 'LT.NS'},
            # HCL Technologies
            {'company_name': 'HCL Technologies', 'stock_symbol': 'HCLTECH.NS'},
            {'company_name': 'HCL Tech', 'stock_symbol': 'HCLTECH.NS'},
            {'company_name': 'HCL', 'stock_symbol': 'HCLTECH.NS'},
            # Maruti Suzuki
            {'company_name': 'Maruti Suzuki', 'stock_symbol': 'MARUTI.NS'},
            {'company_name': 'Maruti', 'stock_symbol': 'MARUTI.NS'},
            # Asian Paints
            {'company_name': 'Asian Paints', 'stock_symbol': 'ASIANPAINT.NS'},
            # Titan Company
            {'company_name': 'Titan Company', 'stock_symbol': 'TITAN.NS'},
            {'company_name': 'Titan', 'stock_symbol': 'TITAN.NS'},
        ]
        
        # US company mappings (recently added)
        us_mappings = [
            {'company_name': 'Apple', 'stock_symbol': 'AAPL'},
            {'company_name': 'Apple Inc', 'stock_symbol': 'AAPL'},
            {'company_name': 'Google', 'stock_symbol': 'GOOGL'},
            {'company_name': 'Alphabet', 'stock_symbol': 'GOOGL'},
            {'company_name': 'Microsoft', 'stock_symbol': 'MSFT'},
            {'company_name': 'Amazon', 'stock_symbol': 'AMZN'},
            {'company_name': 'Tesla', 'stock_symbol': 'TSLA'},
            {'company_name': 'Meta', 'stock_symbol': 'META'},
            {'company_name': 'Facebook', 'stock_symbol': 'META'},
            {'company_name': 'Netflix', 'stock_symbol': 'NFLX'},
            {'company_name': 'NVIDIA', 'stock_symbol': 'NVDA'},
            {'company_name': 'S&P 500', 'stock_symbol': 'SPY'},
            {'company_name': 'NASDAQ', 'stock_symbol': 'QQQ'},
        ]
        
        # Combine mappings - Indian first (original focus), then US (recent addition)
        default_mappings = indian_mappings + us_mappings
        
        # Insert default data
        success = True
        if self.bulk_insert_stocks(default_stocks):
            print("✅ Default stocks initialized")
        else:
            print("❌ Failed to initialize default stocks")
            success = False
        
        if self.bulk_insert_company_mappings(default_mappings):
            print("✅ Default company mappings initialized")
        else:
            print("❌ Failed to initialize default company mappings")
            success = False
        
        return success
    
    def get_active_stocks_with_fallback(self):
        """Get active stocks with fallback to default list if database is empty"""
        try:
            stocks = self.get_active_stocks()
            if not stocks:
                print("📝 No stocks found in database, initializing default data...")
                if self.initialize_default_data():
                    stocks = self.get_active_stocks()
                else:
                    # Fallback to hardcoded list if database initialization fails
                    print("⚠️  Using fallback stock list")
                    stocks = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA', 'SPY', 'QQQ']
            return stocks
        except Exception as e:
            print(f"⚠️  Error getting stocks from database: {e}")
            print("⚠️  Using fallback stock list")
            return ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA', 'SPY', 'QQQ']
    
    def get_company_mappings_with_fallback(self):
        """Get company mappings with fallback to default mappings if database is empty"""
        try:
            mappings = self.get_company_mappings()
            if not mappings:
                print("📝 No company mappings found in database, will initialize on first run...")
                mappings = {
                    'APPLE': 'AAPL', 'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL',
                    'MICROSOFT': 'MSFT', 'AMAZON': 'AMZN', 'TESLA': 'TSLA',
                    'META': 'META', 'FACEBOOK': 'META', 'NETFLIX': 'NFLX',
                    'NVIDIA': 'NVDA', 'S&P 500': 'SPY', 'NASDAQ': 'QQQ'
                }
            return mappings
        except Exception as e:
            print(f"⚠️  Error getting company mappings from database: {e}")
            return {
                'APPLE': 'AAPL', 'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL',
                'MICROSOFT': 'MSFT', 'AMAZON': 'AMZN', 'TESLA': 'TSLA',
                'META': 'META', 'FACEBOOK': 'META', 'NETFLIX': 'NFLX',
                'NVIDIA': 'NVDA', 'S&P 500': 'SPY', 'NASDAQ': 'QQQ'
            }
    
    def cleanup_duplicate_articles(self, dry_run=True):
        """Clean up duplicate articles in the database"""
        from deduplication_utils import NewsDeduplicator
        deduplicator = NewsDeduplicator()
        
        # Use the existing method from deduplication_utils
        return deduplicator.remove_duplicate_articles(dry_run=dry_run)
