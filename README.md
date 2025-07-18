# Stock Sentiment Analysis System

A comprehensive stock sentiment analysis system that collects news articles from RSS feeds, analyzes sentiment using multiple NLP models, and displays results on an interactive web dashboard with intelligent stock search capabilities.

## Features

- **📰 News Collection**: Automatically collects news articles from major financial RSS feeds including Yahoo Finance, Bloomberg, CNBC, Reuters, and MarketWatch
- **🧠 Multi-Model Sentiment Analysis**: Uses three different sentiment analysis models:
  - VADER (Valence Aware Dictionary and sEntiment Reasoner) - Always enabled
  - TextBlob - Always enabled
  - FinBERT (Financial Domain-Specific BERT) - Optional (disabled by default for faster setup)
- **🔍 Smart Stock Search**: Advanced search functionality that allows you to:
  - Search by stock symbol (e.g., AAPL, GOOGL)
  - Search by company name (e.g., Apple, Google, Microsoft)
  - Get instant stock validation and company information
  - Automatically add new stocks to your watchlist
  - Search from a database of 50+ popular stocks and ETFs
- **📊 Interactive Dashboard**: Real-time web dashboard with:
  - **Search Bar**: Find any stock by name or symbol
  - Current sentiment scores and trends
  - Stock price correlation charts
  - Sentiment distribution analysis
  - Recent news articles with sentiment scores
  - Model comparison charts
  - Time range filtering (1 day to 1 month)
- **⚡ Real-Time Updates**: Automated data collection every 15 minutes
- **🎯 Flexible Stock Tracking**: 
  - Default tracking of major stocks: AAPL, GOOGL, MSFT, AMZN, TSLA, META, NFLX, NVDA, SPY, QQQ
  - Search and analyze ANY publicly traded stock
  - Supports stocks, ETFs, and major indices

## Installation

### Prerequisites

- Python 3.7+
- PostgreSQL 12+ (recommended) or SQLite (for development)

### Database Setup

#### Option 1: PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**:
   - Download from https://www.postgresql.org/download/
   - Follow the installation wizard
   - Remember the password you set for the `postgres` user
   - For more Information https://www.w3schools.com/postgresql/postgresql_install.php

2. **Create Database and User**:
   Open PostgreSQL command prompt and run these commands one by one:
   ```sql
   -- Create the database
   CREATE DATABASE stock_sentiment_db;

   -- Create the user
   CREATE USER stock_user WITH PASSWORD 'your_secure_password_here';

   -- Grant privileges on the database
   GRANT ALL PRIVILEGES ON DATABASE stock_sentiment_db TO stock_user;

   -- Connect to the database (this needs to be done separately)
   \c stock_sentiment_db

   -- Grant schema permissions
   GRANT ALL ON SCHEMA public TO stock_user;
   GRANT ALL ON ALL TABLES IN SCHEMA public TO stock_user;
   GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO stock_user;

   -- Set default privileges for future tables
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO stock_user;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO stock_user;

   -- Show users to verify
   \du

   -- quit
   \q
   ```

3. **Configure Environment**:
   Create a `.env` file in the project root:
   ```
   # Database Configuration
   DB_TYPE=postgresql
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=stock_sentiment_db
   DB_USER=stock_user
   DB_PASSWORD=your_secure_password_here
   ```

#### Option 2: SQLite (for Development)

1. **Configure Environment**:
   Create a `.env` file in the project root:
   ```
   # Database Configuration
   DB_TYPE=sqlite
   ```

### Application Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements-minimal.txt
   pip install psycopg2-binary  # Only for PostgreSQL
   ```

2. **Initialize Database**:
   ```bash
   python setup_postgres.py
   ```
   - Choose option 5 (Full setup) to create tables and migrate initial data

3. **Run the Application**:
   ```bash
   python main.py
   ```

4. **Access the Dashboard** at http://127.0.0.1:8050

### Enhanced Installation (with FinBERT)

If you want to enable the FinBERT model for more accurate financial sentiment analysis:

1. **Install full dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Enable FinBERT** in `config.py`:
   ```python
   SENTIMENT_MODELS = {
       'vader': True,
       'textblob': True,
       'finbert': True  # Change this to True
   }
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

**Note**: The full installation requires ~2GB additional space and longer initial setup time due to the FinBERT model download.

## Project Structure

```
stock_sentiment_analysis/
├── main.py                    # Main application entry point
├── config.py                 # Configuration settings
├── data_collector.py         # RSS feed collection and stock data
├── sentiment_analyzer.py     # Sentiment analysis engine
├── dashboard.py              # Web dashboard interface
├── database.py               # Database models and management
├── stock_lookup.py           # Stock search and validation utilities
├── setup_postgres.py         # Database setup and management script
├── setup_database.sql        # SQL script for database initialization
├── requirements.txt          # Full Python dependencies (with FinBERT)
├── requirements-minimal.txt  # Minimal dependencies (recommended)
├── .env                      # Environment configuration (create this)
└── README.md                # This file
```

## How It Works

1. **Data Collection**: The system automatically fetches news articles from RSS feeds and identifies which stocks they relate to
2. **Sentiment Analysis**: Each article is analyzed using three different models to determine sentiment (positive, negative, neutral)
3. **Data Storage**: All data is stored in PostgreSQL (or SQLite) database for persistence and scalability
4. **Stock Management**: Stock symbols and company mappings are stored in the database for dynamic configuration
5. **Dashboard**: Real-time web interface displays sentiment trends, correlations with stock prices, and recent news
6. **Continuous Updates**: The system runs continuously, updating data every 15 minutes

## Configuration

You can modify the following settings:

### Database Configuration (`.env` file)
- **DB_TYPE**: Database type (`postgresql` or `sqlite`)
- **DB_HOST**: Database host (default: `localhost`)
- **DB_PORT**: Database port (default: `5432`)
- **DB_NAME**: Database name (default: `stock_sentiment_db`)
- **DB_USER**: Database user (default: `stock_user`)
- **DB_PASSWORD**: Database password

### Application Settings (`config.py`)
- **COLLECT_INTERVAL_MINUTES**: How often to collect new data (default: 15 minutes)
- **NEWS_RSS_FEEDS**: RSS feed URLs to monitor
- **DASHBOARD_PORT**: Port for the web dashboard (default: 8050)

### Stock Management
- **Dynamic Stock Tracking**: Stock symbols are now stored in the database
- **Add/Remove Stocks**: Use the dashboard search or database management tools
- **Company Mappings**: Extensive company name to symbol mappings in the database

### Sentiment Analysis Models
- **SENTIMENT_MODELS**: Control which models to use:
  ```python
  SENTIMENT_MODELS = {
      'vader': True,      # Always enabled - fast and reliable
      'textblob': True,   # Always enabled - good general performance
      'finbert': False    # Optional - best for financial text but slower
  }
  ```

### Stock Search & Database Management
- **Database-Driven**: All stock symbols and company mappings stored in the database
- **Search Coverage**: Includes tech giants, financial institutions, ETFs, and major indices
- **Dynamic Expansion**: System automatically validates and adds new stocks via search
- **Management Tools**: Use `python setup_postgres.py` for database management

### Data Sources
- **RSS Feeds**: Yahoo Finance, Bloomberg, CNBC, Reuters, MarketWatch
- **Stock Data**: Real-time prices via Yahoo Finance API
- **Search Validation**: Live stock symbol validation

## Dashboard Features

### 🔍 Smart Search
- **Universal Stock Search**: Search any stock by symbol or company name
- **Instant Validation**: Real-time stock symbol validation using Yahoo Finance
- **Auto-Complete**: Smart suggestions based on partial matches
- **Dynamic Watchlist**: Automatically add searched stocks to your dropdown
- **Company Information**: Get full company names and details

### 📊 Analytics & Visualization
- **Summary Cards**: Current sentiment score, total articles analyzed, and real-time stock prices
- **Sentiment vs Stock Price**: Dual-axis correlation chart showing sentiment trends alongside stock prices
- **Sentiment Distribution**: Interactive pie chart showing positive/negative/neutral sentiment breakdown
- **Timeline Chart**: Historical sentiment trends over time with multiple data sources
- **Recent Articles**: Live feed of recent news articles with sentiment scores and source attribution
- **Model Comparison**: Performance comparison of VADER, TextBlob, and FinBERT models
- **Time Range Filtering**: Analyze data from 1 day to 1 month periods

### 🎯 Stock Coverage
- **Default Watchlist**: Pre-configured with major stocks (AAPL, GOOGL, MSFT, AMZN, TSLA, META, NFLX, NVDA, SPY, QQQ)
- **Extended Database**: 50+ popular stocks and ETFs with company name mappings
- **Universal Support**: Search and analyze any publicly traded stock
- **Real-time Prices**: Live stock price data with daily change indicators

## Requirements

### System Requirements
- Python 3.7+
- PostgreSQL 12+ (recommended) or SQLite (for development)
- Internet connection for RSS feeds and stock data
- ~500MB free disk space (minimal installation)
- ~2GB free disk space (full installation with FinBERT)

### Dependencies
- **Minimal Setup**: Uses lightweight models (VADER + TextBlob) for fast performance
- **Full Setup**: Includes FinBERT transformer model for enhanced financial sentiment analysis
- **No API Keys Required**: Works entirely with public RSS feeds and Yahoo Finance data
- **Cross-Platform**: Compatible with Windows, macOS, and Linux

## No API Keys Required

This system works entirely with public RSS feeds and Yahoo Finance data. No API keys, authentication, or paid services required. It's ready to run out of the box!

### What You Get Without API Keys:
- ✅ Real-time news sentiment analysis
- ✅ Live stock price data
- ✅ Universal stock search
- ✅ Interactive dashboard
- ✅ Historical trend analysis
- ✅ Multiple sentiment models

## How to Use

### Basic Usage
1. **Start the application**: Run `python main.py`
2. **Access dashboard**: Open http://127.0.0.1:8050 in your browser
3. **Search stocks**: Use the search bar to find any stock by name or symbol
4. **Analyze sentiment**: Select stocks from the dropdown and choose time ranges
5. **Monitor trends**: Watch real-time sentiment updates every 15 minutes

### Search Examples
- **By Symbol**: AAPL, GOOGL, MSFT, TSLA
- **By Company**: Apple, Google, Microsoft, Tesla
- **Partial Names**: "Bank of America" → BAC, "JP Morgan" → JPM
- **ETFs**: "S&P 500" → SPY, "Nasdaq" → QQQ

### Advanced Features
- **Time Range Analysis**: Compare sentiment over different periods
- **Model Comparison**: See how different AI models rate the same content
- **Price Correlation**: Identify relationships between sentiment and stock movement
- **Source Attribution**: Track which news sources are most influential

## Troubleshooting

### Common Issues
1. **Installation Problems**:
   - Try `pip install -r requirements-minimal.txt` for faster setup
   - Ensure Python 3.7+ is installed
   - Use virtual environment if encountering conflicts
   - For PostgreSQL, ensure `psycopg2-binary` is installed

2. **Database Issues**:
   - Check PostgreSQL service is running
   - Verify database credentials in `.env` file
   - Run `python setup_postgres.py` to test connection
   - Use SQLite for development if PostgreSQL issues persist

3. **Dashboard Issues**:
   - Check if port 8050 is available
   - Change `DASHBOARD_PORT` in `config.py` if needed
   - Ensure internet connection for RSS feeds

4. **Search Not Working**:
   - Verify internet connection for stock validation
   - Try exact stock symbols if company names don't work
   - Check Yahoo Finance for symbol availability

5. **Performance Issues**:
   - Use minimal installation for faster startup
   - Disable FinBERT if system resources are limited
   - Adjust collection interval in config
   - Use PostgreSQL connection pooling for better performance

### First Run Notes
- Initial startup may take 1-2 minutes to download NLTK data
- FinBERT model download requires additional 1-2GB and time
- Some RSS feeds may be temporarily unavailable

## License

This project is open source and available under the MIT License.
