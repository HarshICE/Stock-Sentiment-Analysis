import nltk
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
import pandas as pd
from datetime import datetime
import re
from config import Config
from database import DatabaseManager, NewsArticle, SentimentAnalysis

class SentimentAnalyzer:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.finbert_analyzer = None
        self._setup_models()
    
    def _setup_models(self):
        """Initialize sentiment analysis models"""
        # Download required NLTK data
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
        except:
            pass
        
        # Initialize FinBERT for financial sentiment analysis
        if Config.SENTIMENT_MODELS.get('finbert', False):
            try:
                model_name = "ProsusAI/finbert"
                self.finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.finbert_analyzer = pipeline(
                    "sentiment-analysis",
                    model=self.finbert_model,
                    tokenizer=self.finbert_tokenizer,
                    return_all_scores=True
                )
            except Exception as e:
                print(f"Error loading FinBERT model: {e}")
                self.finbert_analyzer = None
    
    def preprocess_text(self, text):
        """Clean and preprocess text for sentiment analysis"""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions and hashtags symbols but keep the text
        text = re.sub(r'[@#]', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def analyze_vader_sentiment(self, text):
        """Analyze sentiment using VADER"""
        if not text:
            return 0.0, 'neutral'
        
        scores = self.vader_analyzer.polarity_scores(text)
        compound_score = scores['compound']
        
        # Classify sentiment
        if compound_score >= 0.05:
            sentiment_label = 'positive'
        elif compound_score <= -0.05:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        return compound_score, sentiment_label
    
    def analyze_textblob_sentiment(self, text):
        """Analyze sentiment using TextBlob"""
        if not text:
            return 0.0, 'neutral'
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classify sentiment
        if polarity > 0.1:
            sentiment_label = 'positive'
        elif polarity < -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        return polarity, sentiment_label
    
    def analyze_finbert_sentiment(self, text):
        """Analyze sentiment using FinBERT"""
        if not text or not self.finbert_analyzer:
            return 0.0, 'neutral'
        
        try:
            # Truncate text if too long
            if len(text) > 512:
                text = text[:512]
            
            results = self.finbert_analyzer(text)
            
            # Find the highest confidence score
            sentiment_scores = {result['label'].lower(): result['score'] for result in results[0]}
            
            # Convert to numerical score
            if 'positive' in sentiment_scores:
                pos_score = sentiment_scores.get('positive', 0)
                neg_score = sentiment_scores.get('negative', 0)
                neu_score = sentiment_scores.get('neutral', 0)
                
                # Calculate compound score
                compound_score = pos_score - neg_score
                
                # Determine label
                if pos_score > neg_score and pos_score > neu_score:
                    sentiment_label = 'positive'
                elif neg_score > pos_score and neg_score > neu_score:
                    sentiment_label = 'negative'
                else:
                    sentiment_label = 'neutral'
                
                return compound_score, sentiment_label
            
        except Exception as e:
            print(f"Error in FinBERT analysis: {e}")
        
        return 0.0, 'neutral'
    
    def analyze_text_sentiment(self, text):
        """Analyze sentiment using all available models"""
        preprocessed_text = self.preprocess_text(text)
        
        results = {
            'preprocessed_text': preprocessed_text,
            'vader_score': 0.0,
            'vader_label': 'neutral',
            'textblob_score': 0.0,
            'textblob_label': 'neutral',
            'finbert_score': 0.0,
            'finbert_label': 'neutral',
            'combined_score': 0.0,
            'combined_label': 'neutral'
        }
        
        # VADER analysis
        if Config.SENTIMENT_MODELS.get('vader', False):
            vader_score, vader_label = self.analyze_vader_sentiment(preprocessed_text)
            results['vader_score'] = vader_score
            results['vader_label'] = vader_label
        
        # TextBlob analysis
        if Config.SENTIMENT_MODELS.get('textblob', False):
            textblob_score, textblob_label = self.analyze_textblob_sentiment(preprocessed_text)
            results['textblob_score'] = textblob_score
            results['textblob_label'] = textblob_label
        
        # FinBERT analysis
        if Config.SENTIMENT_MODELS.get('finbert', False):
            finbert_score, finbert_label = self.analyze_finbert_sentiment(preprocessed_text)
            results['finbert_score'] = finbert_score
            results['finbert_label'] = finbert_label
        
        # Combine scores (weighted average)
        weights = {'vader': 0.3, 'textblob': 0.2, 'finbert': 0.5}
        combined_score = (
            weights['vader'] * results['vader_score'] +
            weights['textblob'] * results['textblob_score'] +
            weights['finbert'] * results['finbert_score']
        )
        
        # Determine combined label
        if combined_score >= 0.1:
            combined_label = 'positive'
        elif combined_score <= -0.1:
            combined_label = 'negative'
        else:
            combined_label = 'neutral'
        
        results['combined_score'] = combined_score
        results['combined_label'] = combined_label
        
        return results
    
    def analyze_news_articles(self):
        """Analyze sentiment of news articles in database"""
        session = self.db_manager.get_session()
        
        try:
            # Get articles without sentiment analysis
            articles = session.query(NewsArticle).filter(
                NewsArticle.sentiment_score.is_(None)
            ).all()
            
            print(f"Analyzing sentiment for {len(articles)} news articles...")
            
            for article in articles:
                text = f"{article.title} {article.content}"
                sentiment_results = self.analyze_text_sentiment(text)
                
                # Update article with sentiment scores
                article.sentiment_score = sentiment_results['combined_score']
                article.sentiment_label = sentiment_results['combined_label']
                article.vader_score = sentiment_results['vader_score']
                article.textblob_score = sentiment_results['textblob_score']
                article.finbert_score = sentiment_results['finbert_score']
            
            session.commit()
            print(f"Completed sentiment analysis for {len(articles)} news articles")
            
        except Exception as e:
            session.rollback()
            print(f"Error analyzing news articles: {e}")
        finally:
            self.db_manager.close_session(session)
    
    def calculate_aggregated_sentiment(self):
        """Calculate aggregated sentiment scores by symbol and date"""
        session = self.db_manager.get_session()
        
        try:
            # Get all symbols from database
            db_manager = DatabaseManager()
            symbols = db_manager.get_active_stocks()
            
            for symbol in symbols:
                # Calculate daily sentiment aggregates
                self._calculate_daily_sentiment(session, symbol)
            
            session.commit()
            print("Completed aggregated sentiment calculation")
            
        except Exception as e:
            session.rollback()
            print(f"Error calculating aggregated sentiment: {e}")
        finally:
            self.db_manager.close_session(session)
    
    def _calculate_daily_sentiment(self, session, symbol):
        """Calculate daily sentiment for a specific symbol"""
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Query news sentiment for today
        news_articles = session.query(NewsArticle).filter(
            and_(
                NewsArticle.stock_symbol == symbol,
                func.date(NewsArticle.created_at) == today
            )
        ).all()
        
        # Calculate news sentiment
        news_scores = [article.sentiment_score for article in news_articles if article.sentiment_score is not None]
        news_avg = sum(news_scores) / len(news_scores) if news_scores else 0
        news_count = len(news_articles)
        
        # Count sentiment labels for news
        news_positive = sum(1 for article in news_articles if article.sentiment_label == 'positive')
        news_negative = sum(1 for article in news_articles if article.sentiment_label == 'negative')
        news_neutral = sum(1 for article in news_articles if article.sentiment_label == 'neutral')
        
        # Use only news sentiment (no Twitter data)
        if news_count > 0:
            # Create or update sentiment analysis record
            sentiment_record = SentimentAnalysis(
                symbol=symbol,
                date=datetime.utcnow(),
                avg_sentiment=news_avg,
                sentiment_count=news_count,
                positive_count=news_positive,
                negative_count=news_negative,
                neutral_count=news_neutral,
                news_sentiment=news_avg
            )
            
            session.add(sentiment_record)
    
    def run_full_analysis(self):
        """Run complete sentiment analysis pipeline"""
        print("Starting full sentiment analysis...")
        
        # Analyze news articles
        self.analyze_news_articles()
        
        # Calculate aggregated sentiment
        self.calculate_aggregated_sentiment()
        
        print("Full sentiment analysis completed!")

if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    analyzer.run_full_analysis()
