#!/usr/bin/env python3
"""
Simple Setup Script for Stock Sentiment Analysis System
This script helps new users get started quickly with minimal configuration.
"""

import os
import sys
import shutil
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("=" * 60)
    print("🚀 Stock Sentiment Analysis System - Setup")
    print("=" * 60)
    print("Welcome! This script will help you set up the application quickly.")
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7+ is required!")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} - OK")
    return True

def create_env_file():
    """Create .env file for new users"""
    print("\n📝 Setting up configuration...")
    
    env_path = Path('.env')
    env_template_path = Path('.env.template')
    
    if env_path.exists():
        print("ℹ️  .env file already exists, skipping creation")
        return True
    
    if env_template_path.exists():
        shutil.copy(env_template_path, env_path)
        print("✅ Created .env file from template")
    else:
        # Create basic .env file
        with open(env_path, 'w') as f:
            f.write("""# Database Configuration
# Choose your database type: 'sqlite' (recommended for beginners) or 'postgresql'
DB_TYPE=sqlite

# SQLite Configuration (no additional setup required)
# The database file will be created automatically as 'stock_sentiment.db'

# Note: For first-time users, we recommend using SQLite (DB_TYPE=sqlite)
# It requires no additional database installation or configuration.
""")
        print("✅ Created .env file with SQLite configuration")
    
    return True

def install_requirements():
    """Guide user through installing requirements"""
    print("\n📦 Installing Python packages...")
    
    requirements_minimal = Path('requirements-minimal.txt')
    requirements_full = Path('requirements.txt')
    
    if not requirements_minimal.exists():
        print("❌ Error: requirements-minimal.txt not found!")
        return False
    
    print("Choose installation type:")
    print("1. 🏃 Quick Setup (recommended for beginners)")
    print("   - Uses lightweight sentiment models (VADER + TextBlob)")
    print("   - Faster installation (~200MB)")
    print("   - No GPU required")
    print()
    print("2. 🚀 Full Setup (advanced users)")
    print("   - Includes FinBERT model for financial sentiment analysis")
    print("   - Larger installation (~2GB)")
    print("   - Better accuracy for financial text")
    print()
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            break
        print("Please enter 1 or 2")
    
    if choice == '1':
        print("\n🏃 Installing minimal requirements...")
        cmd = f"{sys.executable} -m pip install -r requirements-minimal.txt"
        print(f"Running: {cmd}")
        result = os.system(cmd)
        
        if result == 0:
            print("✅ Minimal requirements installed successfully!")
            return True
        else:
            print("❌ Error installing requirements. Please check the output above.")
            return False
    
    else:
        print("\n🚀 Installing full requirements...")
        cmd = f"{sys.executable} -m pip install -r requirements.txt"
        print(f"Running: {cmd}")
        result = os.system(cmd)
        
        if result == 0:
            print("✅ Full requirements installed successfully!")
            print("📝 Don't forget to enable FinBERT in config.py if you want to use it!")
            return True
        else:
            print("❌ Error installing requirements. Please check the output above.")
            return False

def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        # Import after requirements are installed
        from config import Config
        from database import DatabaseManager
        
        print(f"📊 Database type: {Config.DB_TYPE}")
        print(f"📊 Database URL: {Config.DATABASE_URL}")
        
        # Try to create DatabaseManager (this will create tables)
        db_manager = DatabaseManager()
        print("✅ Database connection successful!")
        print("✅ Database tables created successfully!")
        
        # Initialize default data
        stocks = db_manager.get_active_stocks_with_fallback()
        print(f"✅ Initialized {len(stocks)} default stocks")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 This might be normal if you haven't installed requirements yet.")
        return False

def print_next_steps():
    """Print what to do next"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    print("To start the application:")
    print("1. Run: python main.py")
    print("2. Open your browser to: http://127.0.0.1:8050")
    print("3. Start analyzing stock sentiment!")
    print()
    print("📚 What the application does:")
    print("• Collects news from major financial sources")
    print("• Analyzes sentiment using AI models")
    print("• Shows results on an interactive dashboard")
    print("• Updates data every 15 minutes")
    print()
    print("🔧 Configuration:")
    print("• Database: SQLite (stock_sentiment.db)")
    print("• Models: VADER + TextBlob")
    print("• Stocks: AAPL, GOOGL, MSFT, AMZN, TSLA, META, NFLX, NVDA, SPY, QQQ")
    print()
    print("💡 Need help? Check the README.md file!")
    print("=" * 60)

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Test database connection
    test_database_connection()
    
    # Print next steps
    print_next_steps()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
