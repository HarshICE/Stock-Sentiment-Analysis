import feedparser
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import re
from config import Config
from database import DatabaseManager
from deduplication_utils import NewsDeduplicator
from region_manager import RegionManager

class NewsCollector:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = Config()
        self.region_manager = RegionManager()
        
        # Get region-specific RSS feeds
        current_region = self.region_manager.get_current_region()
        self.rss_feeds = self.region_manager.get_region_rss_feeds(current_region)
        
        # Fetch stock symbols from the database instead of config
        db_manager = DatabaseManager()
        self.stock_symbols = db_manager.get_active_stocks()
        # Initialize deduplicator
        self.deduplicator = NewsDeduplicator()
        
        print(f"📍 Using {current_region} region with {len(self.rss_feeds)} RSS feeds")
    
    def collect_news_from_rss(self):
        """Collect news articles from RSS feeds"""
        articles = []
        
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                source = self._extract_source_from_url(feed_url)
                
                for entry in feed.entries[:Config.MAX_NEWS_ARTICLES]:
                    article = {
                        'title': entry.title,
                        'url': entry.link,
                        'source': source,
                        'published_date': self._parse_date(entry.get('published')),
                        'content': self._extract_content(entry)
                    }
                    
                    # Determine which stock this article relates to
                    stock_symbol = self._identify_stock_symbol(article['title'] + ' ' + article['content'])
                    if stock_symbol:
                        article['stock_symbol'] = stock_symbol
                        
                        # Check for duplicates before adding
                        duplicate_check = self.deduplicator.is_duplicate_article(article)
                        if not duplicate_check['is_duplicate']:
                            articles.append(article)
                        else:
                            print(f"Skipping duplicate article: {article['title'][:50]}... ({duplicate_check['reason']})")
                        
            except Exception as e:
                print(f"Error collecting from {feed_url}: {e}")
        
        return articles
    
    def _extract_source_from_url(self, url):
        """Extract source name from URL - Supporting Indian and US sources"""
        # Indian sources (original market focus)
        if 'ndtv' in url:
            return 'NDTV Business'
        elif 'economictimes' in url:
            return 'Economic Times'
        elif 'business-standard' in url:
            return 'Business Standard'
        elif 'moneycontrol' in url:
            return 'MoneyControl'
        elif 'livemint' in url:
            return 'LiveMint'
        elif 'financialexpress' in url:
            return 'Financial Express'
        elif 'zeenews' in url:
            return 'Zee News Business'
        elif 'thehindubusinessline' in url:
            return 'The Hindu Business Line'
        # US sources (recently added)
        elif 'yahoo' in url:
            return 'Yahoo Finance'
        elif 'bloomberg' in url:
            return 'Bloomberg'
        elif 'cnbc' in url:
            return 'CNBC'
        elif 'reuters' in url:
            return 'Reuters'
        elif 'marketwatch' in url:
            return 'MarketWatch'
        else:
            return 'Unknown'
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return datetime.utcnow()
        
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return datetime.utcnow()
    
    def _extract_content(self, entry):
        """Extract content from RSS entry"""
        content = entry.get('summary', '')
        if not content:
            content = entry.get('description', '')
        
        # Clean HTML tags
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
        
        return content
    
    def _identify_stock_symbol(self, text):
        """Identify which stock symbol the text is about"""
        text = text.upper()
        
        # Company name mappings
        company_mappings = {
            'APPLE': 'AAPL',
            'GOOGLE': 'GOOGL',
            'ALPHABET': 'GOOGL',
            'MICROSOFT': 'MSFT',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'META': 'META',
            'FACEBOOK': 'META',
            'NETFLIX': 'NFLX',
            'NVIDIA': 'NVDA'
        }
        
        # Check for direct symbol mentions
        for symbol in self.stock_symbols:
            if symbol in text:
                return symbol
        
        # Check for company names
        for company, symbol in company_mappings.items():
            if company in text:
                return symbol
        
        return None


class StockDataCollector:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def collect_stock_prices(self, symbols=None):
        """Collect current stock prices"""
        if symbols is None:
            # Get active stocks from database
            db_manager = DatabaseManager()
            symbols = db_manager.get_active_stocks()
        
        stock_data = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                
                if not hist.empty:
                    latest = hist.iloc[-1]
                    stock_data.append({
                        'symbol': symbol,
                        'price': latest['Close'],
                        'volume': latest['Volume'],
                        'timestamp': datetime.utcnow(),
                        'open_price': latest['Open'],
                        'high_price': latest['High'],
                        'low_price': latest['Low'],
                        'close_price': latest['Close']
                    })
            except Exception as e:
                print(f"Error collecting stock data for {symbol}: {e}")
        
        return stock_data

class DataCollectionOrchestrator:
    def __init__(self):
        self.news_collector = NewsCollector()
        self.stock_collector = StockDataCollector()
        self.db_manager = DatabaseManager()
    
    def collect_all_data(self):
        """Collect all data: news and stock prices"""
        print("Starting data collection...")
        
        # Collect news articles
        print("Collecting news articles...")
        news_articles = self.news_collector.collect_news_from_rss()
        print(f"Collected {len(news_articles)} news articles")
        
        # Collect stock prices
        print("Collecting stock prices...")
        stock_prices = self.stock_collector.collect_stock_prices()
        print(f"Collected {len(stock_prices)} stock prices")
        
        # Save to database
        print("Saving to database...")
        self._save_collected_data(news_articles, stock_prices)
        
        print("Data collection completed!")
    
    def _save_collected_data(self, news_articles, stock_prices):
        """Save collected data to database"""
        # Save news articles (duplicates already filtered out)
        saved_articles = 0
        for article in news_articles:
            if self.db_manager.save_news_article(article):
                saved_articles += 1
        print(f"Saved {saved_articles} news articles (duplicates filtered out)")
        
        # Save stock prices
        saved_prices = 0
        for price in stock_prices:
            if self.db_manager.save_stock_price(price):
                saved_prices += 1
        print(f"Saved {saved_prices} stock prices")

if __name__ == "__main__":
    collector = DataCollectionOrchestrator()
    collector.collect_all_data()
