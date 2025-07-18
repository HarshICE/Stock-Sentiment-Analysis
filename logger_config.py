import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create a custom logger
    logger = logging.getLogger('stock_sentiment_app')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler for all logs (rotating)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler for info and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    # Set up loggers for different modules
    setup_module_loggers()
    
    return logger

def setup_module_loggers():
    """Setup loggers for different modules"""
    modules = ['dashboard', 'data_collector', 'sentiment_analyzer', 'database', 'stock_lookup']
    
    for module in modules:
        module_logger = logging.getLogger(f'stock_sentiment_app.{module}')
        module_logger.setLevel(logging.DEBUG)
        
        # Create module-specific log file
        module_handler = RotatingFileHandler(
            os.path.join('logs', f'{module}.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2
        )
        module_handler.setLevel(logging.DEBUG)
        module_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        ))
        
        module_logger.addHandler(module_handler)
    
    # Setup sync-specific loggers
    setup_sync_loggers()

def setup_sync_loggers():
    """Setup sync-specific loggers"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Sync Operations Logger
    sync_operations_logger = logging.getLogger('sync_operations')
    sync_operations_logger.setLevel(logging.INFO)
    
    sync_ops_handler = RotatingFileHandler(
        os.path.join('logs', 'sync_operations.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    sync_ops_handler.setLevel(logging.INFO)
    sync_ops_handler.setFormatter(logging.Formatter(
        '%(asctime)s - SYNC_OPS - %(levelname)s - %(message)s'
    ))
    sync_operations_logger.addHandler(sync_ops_handler)
    
    # Sync Errors Logger
    sync_errors_logger = logging.getLogger('sync_errors')
    sync_errors_logger.setLevel(logging.ERROR)
    
    sync_errors_handler = RotatingFileHandler(
        os.path.join('logs', 'sync_errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    sync_errors_handler.setLevel(logging.ERROR)
    sync_errors_handler.setFormatter(logging.Formatter(
        '%(asctime)s - SYNC_ERROR - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    ))
    sync_errors_logger.addHandler(sync_errors_handler)
    
    # Database Sync Manager Logger
    database_sync_manager_logger = logging.getLogger('database_sync_manager')
    database_sync_manager_logger.setLevel(logging.INFO)
    
    db_sync_handler = RotatingFileHandler(
        os.path.join('logs', 'database_sync_manager.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    db_sync_handler.setLevel(logging.INFO)
    db_sync_handler.setFormatter(logging.Formatter(
        '%(asctime)s - DB_SYNC - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    ))
    database_sync_manager_logger.addHandler(db_sync_handler)

def get_logger(module_name='stock_sentiment_app'):
    """Get logger for a specific module"""
    return logging.getLogger(module_name)

# Action logger for tracking user actions and system events
class ActionLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        self.logger = logging.getLogger('stock_sentiment_app.actions')
        self.logger.setLevel(logging.INFO)
        
        # Create action log file
        action_handler = RotatingFileHandler(
            os.path.join('logs', 'actions.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        action_handler.setLevel(logging.INFO)
        action_handler.setFormatter(logging.Formatter(
            '%(asctime)s - ACTION - %(message)s'
        ))
        
        self.logger.addHandler(action_handler)
    
    def log_action(self, action, details=None, user_id=None):
        """Log user actions and system events"""
        message = f"Action: {action}"
        if user_id:
            message += f" | User: {user_id}"
        if details:
            message += f" | Details: {details}"
        
        self.logger.info(message)
    
    def log_data_collection(self, articles_count, prices_count, errors=None):
        """Log data collection results"""
        message = f"Data Collection - Articles: {articles_count}, Prices: {prices_count}"
        if errors:
            message += f" | Errors: {errors}"
        self.logger.info(message)
    
    def log_sentiment_analysis(self, analyzed_count, errors=None):
        """Log sentiment analysis results"""
        message = f"Sentiment Analysis - Analyzed: {analyzed_count}"
        if errors:
            message += f" | Errors: {errors}"
        self.logger.info(message)
    
    def log_chart_generation(self, chart_type, symbol, success=True, error=None):
        """Log chart generation events"""
        status = "SUCCESS" if success else "FAILED"
        message = f"Chart Generation - Type: {chart_type}, Symbol: {symbol}, Status: {status}"
        if error:
            message += f" | Error: {error}"
        self.logger.info(message)
    
    def log_search(self, query, results_count, success=True):
        """Log search operations"""
        status = "SUCCESS" if success else "FAILED"
        message = f"Search - Query: '{query}', Results: {results_count}, Status: {status}"
        self.logger.info(message)

# Initialize the action logger
action_logger = ActionLogger()

# Initialize logging when module is imported
if __name__ != '__main__':
    setup_logging()
