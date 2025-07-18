import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Market Configuration - Originally built for Indian markets
    DEFAULT_MARKET = 'US'  # IN for India, US for United States
    
    # News RSS Feeds - Indian market focused (original), US market added recently
    INDIAN_RSS_FEEDS = [
        'https://feeds.feedburner.com/NDTV-Business',
        'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
        'https://www.business-standard.com/rss/markets-106.rss',
        'https://www.moneycontrol.com/rss/business.xml',
        'https://www.livemint.com/rss/money',
        'https://www.financialexpress.com/market/rss/',
        'https://zeenews.india.com/rss/business.xml',
        'https://www.thehindubusinessline.com/markets/?service=rss'
    ]
    
    # US Market RSS Feeds - Recently added for expansion
    US_RSS_FEEDS = [
        'https://feeds.finance.yahoo.com/rss/2.0/headline',
        'https://feeds.bloomberg.com/markets/news.rss',
        'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'https://feeds.reuters.com/reuters/businessNews',
        'https://www.marketwatch.com/rss/topstories'
    ]
    
    # Combined feeds based on default market
    @property
    def NEWS_RSS_FEEDS(self):
        if self.DEFAULT_MARKET == 'IN':
            return self.INDIAN_RSS_FEEDS + self.US_RSS_FEEDS  # Indian feeds first
        else:
            return self.US_RSS_FEEDS + self.INDIAN_RSS_FEEDS  # US feeds first
    
    # For backward compatibility, create a class-level property
    def get_news_rss_feeds(self):
        return self.NEWS_RSS_FEEDS
    
    # Database Configuration - Support both PostgreSQL and SQLite
    DB_TYPE = os.getenv('DB_TYPE', 'SQLite').lower()
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'stock_sentiment_db')
    DB_USER = os.getenv('DB_USER', 'stock_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD')  # No default password - must be set in .env
    
    # Build DATABASE_URL based on DB_TYPE
    if DB_TYPE == 'postgresql':
        DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    else:
        # Default to SQLite for easier setup
        DATABASE_URL = 'sqlite:///stock_sentiment.db'
    
    # Sentiment Analysis Settings
    SENTIMENT_MODELS = {
        'vader': True,
        'textblob': True,
        'finbert': False  # Set to True to enable FinBERT (requires transformers + torch)
    }
    
    # Data Collection Settings
    COLLECT_INTERVAL_MINUTES = 15
    MAX_NEWS_ARTICLES = 50
    
    # Dashboard Settings
    DASHBOARD_PORT = 8050
    DASHBOARD_HOST = '127.0.0.1'
    DASHBOARD_DEBUG = True
