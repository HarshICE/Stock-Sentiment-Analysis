import schedule
import time
import threading
from datetime import datetime
import signal
import sys
from config import Config
from data_collector import DataCollectionOrchestrator
from sentiment_analyzer import SentimentAnalyzer
from dashboard import StockSentimentDashboard
from database import DatabaseManager
from logger_config import setup_logging, get_logger, action_logger

class StockSentimentApp:
    def __init__(self):
        self.data_collector = DataCollectionOrchestrator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.dashboard = StockSentimentDashboard()
        self.running = False
        self.dashboard_thread = None
        self.scheduler_thread = None
        self.logger = get_logger('stock_sentiment_app')
    
    def collect_and_analyze_data(self):
        """Collect data and run sentiment analysis"""
        print(f"[{datetime.now()}] Starting data collection and analysis...")
        
        try:
            # Collect data
            self.data_collector.collect_all_data()
            
            # Analyze sentiment
            self.sentiment_analyzer.run_full_analysis()
            
            print(f"[{datetime.now()}] Data collection and analysis completed successfully!")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error during data collection and analysis: {e}")
    
    def schedule_data_collection(self):
        """Schedule regular data collection"""
        # Schedule data collection every configured interval
        schedule.every(Config.COLLECT_INTERVAL_MINUTES).minutes.do(self.collect_and_analyze_data)
        
        print(f"Data collection scheduled every {Config.COLLECT_INTERVAL_MINUTES} minutes")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def start_scheduler(self):
        """Start the scheduler in a separate thread"""
        self.running = True
        scheduler_thread = threading.Thread(target=self.schedule_data_collection)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        return scheduler_thread
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
    
    def shutdown(self):
        """Gracefully shutdown the application"""
        print("\n🛑 Shutting down Stock Sentiment Analysis System...")
        self.logger.info("Application shutdown initiated")
        action_logger.log_action("APPLICATION_SHUTDOWN")
        
        # Stop scheduler
        self.stop_scheduler()
        
        # Give time for threads to finish
        time.sleep(2)
        
        print("✅ Application shutdown completed successfully!")
        self.logger.info("Application shutdown completed")
        sys.exit(0)
    
    def show_status(self):
        """Show current application status"""
        print("\n📊 Stock Sentiment Analysis System Status:")
        print("=" * 50)
        print(f"🔄 Scheduler Running: {'Yes' if self.running else 'No'}")
        print(f"📅 Collection Interval: {Config.COLLECT_INTERVAL_MINUTES} minutes")
        print(f"🌐 Dashboard: http://{Config.DASHBOARD_HOST}:{Config.DASHBOARD_PORT}")
        print(f"📊 Market Focus: {'Indian' if Config.DEFAULT_MARKET == 'IN' else 'US'} Market")
        
        # Show database stats
        try:
            db_manager = DatabaseManager()
            stocks = db_manager.get_active_stocks()
            print(f"📈 Active Stocks: {len(stocks)}")
            indian_stocks = [s for s in stocks if '.NS' in s]
            us_stocks = [s for s in stocks if '.NS' not in s]
            print(f"🇮🇳 Indian Stocks: {len(indian_stocks)}")
            print(f"🇺🇸 US Stocks: {len(us_stocks)}")
        except Exception as e:
            print(f"❌ Database Error: {e}")
        
        print("=" * 50)
    
    def show_help(self):
        """Show available commands"""
        print("\n📋 Available Commands:")
        print("=" * 50)
        print("help     - Show this help message")
        print("status   - Show application status")
        print("collect  - Run data collection manually")
        print("analyze  - Run sentiment analysis manually")
        print("both     - Run both data collection and analysis")
        print("stocks   - Show tracked stocks")
        print("exit     - Exit the application")
        print("quit     - Exit the application")
        print("stop     - Exit the application")
        print("=" * 50)
    
    def show_stocks(self):
        """Show tracked stocks"""
        try:
            db_manager = DatabaseManager()
            stocks = db_manager.get_active_stocks()
            
            print("\n📈 Tracked Stocks:")
            print("=" * 50)
            
            indian_stocks = [s for s in stocks if '.NS' in s]
            us_stocks = [s for s in stocks if '.NS' not in s]
            
            if indian_stocks:
                print("🇮🇳 Indian Stocks (NSE):")
                for stock in indian_stocks:
                    print(f"  • {stock}")
            
            if us_stocks:
                print("🇺🇸 US Stocks:")
                for stock in us_stocks:
                    print(f"  • {stock}")
            
            print("=" * 50)
        except Exception as e:
            print(f"❌ Error fetching stocks: {e}")
    
    def handle_command(self, command):
        """Handle user commands"""
        command = command.strip().lower()
        
        if command in ['exit', 'quit', 'stop']:
            self.shutdown()
        elif command == 'help':
            self.show_help()
        elif command == 'status':
            self.show_status()
        elif command == 'collect':
            print("\n🔄 Running data collection...")
            self.data_collector.collect_all_data()
            print("✅ Data collection completed!")
        elif command == 'analyze':
            print("\n🧠 Running sentiment analysis...")
            self.sentiment_analyzer.run_full_analysis()
            print("✅ Sentiment analysis completed!")
        elif command == 'both':
            print("\n🔄 Running data collection and analysis...")
            self.collect_and_analyze_data()
        elif command == 'stocks':
            self.show_stocks()
        elif command == '':
            pass  # Empty command, do nothing
        else:
            print(f"❌ Unknown command: '{command}'")
            print("Type 'help' for available commands")
    
    def command_loop(self):
        """Interactive command loop"""
        print("\n💬 Interactive mode enabled. Type 'help' for commands or 'exit' to quit.")
        print("" * 50)
        
        while self.running:
            try:
                command = input("📟 Command: ").strip()
                if command:
                    self.handle_command(command)
            except KeyboardInterrupt:
                print("\n🛑 Ctrl+C detected. Use 'exit' command to quit gracefully.")
            except EOFError:
                print("\n🛑 EOF detected. Exiting...")
                self.shutdown()
            except Exception as e:
                print(f"❌ Error processing command: {e}")
    
    def run_initial_setup(self):
        """Run initial data collection and analysis"""
        print("Running initial setup...")
        self.collect_and_analyze_data()
    
    def run(self):
        """Main application runner"""
        print("🚀 Starting Stock Sentiment Analysis System...")
        print("=" * 50)
        
        try:
            # Run initial setup
            self.run_initial_setup()
            
            # Start scheduler
            scheduler_thread = self.start_scheduler()
            
            # Start dashboard in a separate thread
            print(f"🌐 Starting dashboard on http://{Config.DASHBOARD_HOST}:{Config.DASHBOARD_PORT}")
            self.dashboard_thread = threading.Thread(target=self.dashboard.run_server)
            self.dashboard_thread.daemon = True
            self.dashboard_thread.start()
            
            # Start interactive command loop
            self.command_loop()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.shutdown()
        except Exception as e:
            print(f"❌ Error running application: {e}")
            self.shutdown()

def main():
    """Main entry point"""
    # Initialize logging system
    setup_logging()
    logger = get_logger('stock_sentiment_app.main')
    
    logger.info("Starting Stock Sentiment Analysis System")
    action_logger.log_action("APPLICATION_START")
    
    print("Stock Sentiment Analysis System")
    print("=" * 50)
    print("This system will:")
    print("1. Collect news articles from RSS feeds")
    print("2. Analyze sentiment using multiple models (VADER, TextBlob, FinBERT)")
    print("3. Display results on a web dashboard")
    print("4. Update data every", Config.COLLECT_INTERVAL_MINUTES, "minutes")
    print("=" * 50)

    try:
        # Use DatabaseManager to fetch updated configuration with fallback
        db_manager = DatabaseManager()
        stocks = db_manager.get_active_stocks_with_fallback()
        mappings = db_manager.get_company_mappings_with_fallback()

        print("📰 Using RSS feeds from: Yahoo Finance, Bloomberg, CNBC, Reuters, MarketWatch")
        print(f"🧠 Sentiment analysis models: VADER, TextBlob{', FinBERT' if Config.SENTIMENT_MODELS.get('finbert') else ''}")
        print("📊 Tracking stocks:", ", ".join(stocks))
        print("=" * 50)

        logger.info(f"Configuration loaded - {len(stocks)} stocks tracked, {len(mappings)} company mappings")
        
        # Demonstrating database use in your application setup
        app = StockSentimentApp()
        app.run()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        action_logger.log_action("APPLICATION_START_FAILED", str(e))
        raise

if __name__ == "__main__":
    main()
