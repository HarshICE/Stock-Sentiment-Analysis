import hashlib
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from database import DatabaseManager, NewsArticle
from sqlalchemy import func, and_

class NewsDeduplicator:
    def __init__(self, similarity_threshold=0.8, title_threshold=0.9):
        """
        Initialize the news deduplicator
        
        Args:
            similarity_threshold: Content similarity threshold (0-1)
            title_threshold: Title similarity threshold (0-1)
        """
        self.db_manager = DatabaseManager()
        self.similarity_threshold = similarity_threshold
        self.title_threshold = title_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def normalize_text(self, text):
        """Normalize text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove special characters and numbers
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def compute_content_hash(self, title, content):
        """Compute hash for content-based deduplication"""
        normalized_title = self.normalize_text(title)
        normalized_content = self.normalize_text(content)
        combined_text = f"{normalized_title} {normalized_content}"
        return hashlib.md5(combined_text.encode()).hexdigest()
    
    def compute_title_similarity(self, title1, title2):
        """Compute similarity between two titles"""
        if not title1 or not title2:
            return 0.0
        
        norm_title1 = self.normalize_text(title1)
        norm_title2 = self.normalize_text(title2)
        
        return SequenceMatcher(None, norm_title1, norm_title2).ratio()
    
    def compute_content_similarity(self, content1, content2):
        """Compute similarity between two content pieces using TF-IDF"""
        if not content1 or not content2:
            return 0.0
        
        norm_content1 = self.normalize_text(content1)
        norm_content2 = self.normalize_text(content2)
        
        if len(norm_content1) < 10 or len(norm_content2) < 10:
            return 0.0
        
        try:
            # Compute TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform([norm_content1, norm_content2])
            
            # Compute cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return similarity
        except Exception as e:
            print(f"Error computing content similarity: {e}")
            return 0.0
    
    def is_duplicate_by_url(self, url):
        """Check if URL already exists in database"""
        if not url:
            return False
        
        session = self.db_manager.get_session()
        try:
            existing = session.query(NewsArticle).filter(NewsArticle.url == url).first()
            return existing is not None
        finally:
            self.db_manager.close_session(session)
    
    def find_similar_articles(self, title, content, stock_symbol, hours_back=24):
        """Find articles similar to the given one within a time window"""
        if not title and not content:
            return []
        
        session = self.db_manager.get_session()
        try:
            # Get recent articles for the same stock
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            recent_articles = session.query(NewsArticle).filter(
                and_(
                    NewsArticle.stock_symbol == stock_symbol,
                    NewsArticle.created_at >= cutoff_time
                )
            ).all()
            
            similar_articles = []
            
            for article in recent_articles:
                # Check title similarity
                title_sim = self.compute_title_similarity(title, article.title)
                
                # Check content similarity
                content_sim = self.compute_content_similarity(content, article.content)
                
                # Consider it similar if either title or content similarity is high
                if title_sim >= self.title_threshold or content_sim >= self.similarity_threshold:
                    similar_articles.append({
                        'article': article,
                        'title_similarity': title_sim,
                        'content_similarity': content_sim
                    })
            
            return similar_articles
        
        finally:
            self.db_manager.close_session(session)
    
    def is_duplicate_article(self, article_data):
        """
        Check if an article is a duplicate using multiple methods
        
        Args:
            article_data: Dictionary containing article information
            
        Returns:
            Dictionary with duplicate detection results
        """
        result = {
            'is_duplicate': False,
            'duplicate_type': None,
            'similar_articles': [],
            'reason': None
        }
        
        # 1. Check URL-based duplicates
        if self.is_duplicate_by_url(article_data.get('url')):
            result['is_duplicate'] = True
            result['duplicate_type'] = 'url'
            result['reason'] = 'Same URL already exists'
            return result
        
        # 2. Check content-based duplicates
        similar_articles = self.find_similar_articles(
            article_data.get('title', ''),
            article_data.get('content', ''),
            article_data.get('stock_symbol', ''),
            hours_back=24
        )
        
        if similar_articles:
            result['is_duplicate'] = True
            result['duplicate_type'] = 'content'
            result['similar_articles'] = similar_articles
            result['reason'] = f'Found {len(similar_articles)} similar articles'
            return result
        
        return result
    
    def remove_duplicate_articles(self, dry_run=True):
        """
        Remove duplicate articles from database
        
        Args:
            dry_run: If True, only report duplicates without removing them
            
        Returns:
            Dictionary with removal statistics
        """
        session = self.db_manager.get_session()
        stats = {
            'total_articles': 0,
            'url_duplicates': 0,
            'content_duplicates': 0,
            'removed_articles': 0
        }
        
        try:
            # Get all articles ordered by creation date (keep oldest)
            all_articles = session.query(NewsArticle).order_by(NewsArticle.created_at.asc()).all()
            stats['total_articles'] = len(all_articles)
            
            print(f"Analyzing {len(all_articles)} articles for duplicates...")
            
            # Track seen URLs and content hashes
            seen_urls = set()
            seen_hashes = set()
            articles_to_remove = []
            
            for article in all_articles:
                is_duplicate = False
                duplicate_reason = None
                
                # Check URL duplicates
                if article.url and article.url in seen_urls:
                    is_duplicate = True
                    duplicate_reason = "URL duplicate"
                    stats['url_duplicates'] += 1
                elif article.url:
                    seen_urls.add(article.url)
                
                # Check content duplicates
                if not is_duplicate:
                    content_hash = self.compute_content_hash(article.title, article.content)
                    if content_hash in seen_hashes:
                        is_duplicate = True
                        duplicate_reason = "Content duplicate"
                        stats['content_duplicates'] += 1
                    else:
                        seen_hashes.add(content_hash)
                
                if is_duplicate:
                    articles_to_remove.append((article, duplicate_reason))
                    print(f"Duplicate found: {article.title[:50]}... ({duplicate_reason})")
            
            stats['removed_articles'] = len(articles_to_remove)
            
            if not dry_run and articles_to_remove:
                print(f"Removing {len(articles_to_remove)} duplicate articles...")
                for article, reason in articles_to_remove:
                    session.delete(article)
                session.commit()
                print("Duplicate removal completed!")
            elif dry_run:
                print("DRY RUN: No articles were actually removed")
            
            return stats
            
        except Exception as e:
            session.rollback()
            print(f"Error removing duplicates: {e}")
            return stats
        finally:
            self.db_manager.close_session(session)
    
    def analyze_duplicate_patterns(self):
        """Analyze patterns in duplicate articles"""
        session = self.db_manager.get_session()
        
        try:
            # Get articles grouped by source
            from sqlalchemy import func
            
            source_stats = session.query(
                NewsArticle.source,
                func.count(NewsArticle.id).label('count')
            ).group_by(NewsArticle.source).all()
            
            print("\n=== Duplicate Analysis by Source ===")
            for source, count in source_stats:
                print(f"{source}: {count} articles")
            
            # Get articles grouped by stock symbol
            symbol_stats = session.query(
                NewsArticle.stock_symbol,
                func.count(NewsArticle.id).label('count')
            ).group_by(NewsArticle.stock_symbol).all()
            
            print("\n=== Articles by Stock Symbol ===")
            for symbol, count in symbol_stats:
                print(f"{symbol}: {count} articles")
            
            # Find potential title duplicates
            print("\n=== Potential Title Duplicates ===")
            all_articles = session.query(NewsArticle).all()
            
            title_groups = {}
            for article in all_articles:
                normalized_title = self.normalize_text(article.title)
                if normalized_title not in title_groups:
                    title_groups[normalized_title] = []
                title_groups[normalized_title].append(article)
            
            duplicate_titles = {k: v for k, v in title_groups.items() if len(v) > 1}
            
            for norm_title, articles in list(duplicate_titles.items())[:10]:  # Show first 10
                print(f"Title: {norm_title[:50]}...")
                print(f"  Found {len(articles)} similar articles")
                for article in articles:
                    print(f"    - {article.source}: {article.title[:50]}...")
                print()
            
        finally:
            self.db_manager.close_session(session)


def main():
    """Main function for testing deduplication"""
    deduplicator = NewsDeduplicator()
    
    print("=== News Deduplication Analysis ===")
    
    # Analyze current duplicate patterns
    deduplicator.analyze_duplicate_patterns()
    
    # Run duplicate removal (dry run first)
    print("\n=== Duplicate Removal (Dry Run) ===")
    stats = deduplicator.remove_duplicate_articles(dry_run=True)
    
    print(f"\nDuplication Statistics:")
    print(f"Total articles: {stats['total_articles']}")
    print(f"URL duplicates: {stats['url_duplicates']}")
    print(f"Content duplicates: {stats['content_duplicates']}")
    print(f"Total duplicates to remove: {stats['removed_articles']}")
    
    # Ask user if they want to proceed with actual removal
    if stats['removed_articles'] > 0:
        response = input("\nDo you want to remove these duplicates? (y/n): ")
        if response.lower() == 'y':
            print("\n=== Removing Duplicates ===")
            deduplicator.remove_duplicate_articles(dry_run=False)
        else:
            print("Duplicate removal cancelled.")


if __name__ == "__main__":
    main()
