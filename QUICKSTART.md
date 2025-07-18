# 🚀 Quick Start Guide

**Get up and running in 5 minutes!**

## For New Users (Recommended)

### Step 1: Run the Setup Script
```bash
python setup.py
```

This will:
- ✅ Check your Python version
- ✅ Create configuration files
- ✅ Install required packages
- ✅ Set up SQLite database automatically
- ✅ Initialize default stocks

### Step 2: Start the Application
```bash
python main.py
```

### Step 3: Open the Dashboard
Open your browser to: **http://127.0.0.1:8050**

**That's it! You're ready to analyze stock sentiment!**

---

## Manual Setup (Alternative)

If you prefer to set up manually:

### 1. Install Requirements
```bash
pip install -r requirements-minimal.txt
```

### 2. Configure Database
The application is pre-configured to use SQLite (no setup needed).

### 3. Run the Application
```bash
python main.py
```

---

## What You Get

### 📊 **Real-time Stock Sentiment Analysis**
- **10 Popular Stocks**: AAPL, GOOGL, MSFT, AMZN, TSLA, META, NFLX, NVDA, SPY, QQQ
- **News Sources**: Yahoo Finance, Bloomberg, CNBC, Reuters, MarketWatch
- **AI Models**: VADER + TextBlob sentiment analysis
- **Updates**: Every 15 minutes automatically

### 🔍 **Smart Stock Search**
- Search any stock by symbol (e.g., "AAPL") or company name (e.g., "Apple")
- Add new stocks to your watchlist instantly
- Real-time stock price data

### 📈 **Interactive Dashboard**
- Live sentiment scores and trends
- Stock price correlation charts
- Recent news articles with sentiment analysis
- Time range filtering (1 day to 1 month)

---

## Requirements

- **Python 3.7+** ✅
- **Internet connection** (for news feeds and stock data) ✅
- **~200MB disk space** (minimal setup) ✅

**No API keys required!** Works with public data sources.

---

## Troubleshooting

### Common Issues:

1. **"requirements-minimal.txt not found"**
   - Make sure you're in the correct directory
   - Check if the file exists: `ls requirements-minimal.txt`

2. **Python version error**
   - Upgrade to Python 3.7+: Visit https://python.org/downloads

3. **Port 8050 already in use**
   - Close other applications using port 8050
   - Or change the port in `config.py`

4. **Installation errors**
   - Try upgrading pip: `python -m pip install --upgrade pip`
   - Use a virtual environment: `python -m venv venv && source venv/bin/activate`

---

## Advanced Setup

### Enable FinBERT Model (Optional)
For better financial sentiment analysis:

1. Install full requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Enable FinBERT in `config.py`:
   ```python
   SENTIMENT_MODELS = {
       'vader': True,
       'textblob': True,
       'finbert': True  # Change this to True
   }
   ```

**Note**: This requires ~2GB additional download time.

### Use PostgreSQL (Optional)
For production or advanced users:

1. Install PostgreSQL
2. Update `.env` file:
   ```
   DB_TYPE=postgresql
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=stock_sentiment_db
   DB_USER=stock_user
   DB_PASSWORD=your_secure_password_here
   ```

3. Install PostgreSQL driver:
   ```bash
   pip install psycopg2-binary
   ```

---

## Need Help?

- 📖 **Full Documentation**: Check `README.md`
- 🐛 **Issues**: Check the console output for error messages
- 💡 **Tips**: The setup script provides helpful guidance

**Happy analyzing!** 📈
