#!/usr/bin/env python3
"""
Duplicate News Article Cleanup Script for PostgreSQL

This script handles duplicate news articles that can occur when using PostgreSQL,
which was working fine with SQLite. It provides both cleanup for existing duplicates
and prevention for future duplicates.

Usage:
    python cleanup_duplicates.py --analyze     # Analyze duplicates without removing
    python cleanup_duplicates.py --clean       # Remove duplicates
    python cleanup_duplicates.py --help        # Show help

Features:
- URL-based duplicate detection
- Content-based duplicate detection using hashing
- Safe dry-run mode by default
- Detailed reporting of duplicates found
"""

import argparse
import sys
from database import DatabaseManager
from deduplication_utils import NewsDeduplicator
from config import Config

def main():
    parser = argparse.ArgumentParser(
        description="Clean up duplicate news articles in PostgreSQL database"
    )
    parser.add_argument(
        '--analyze', 
        action='store_true',
        help='Analyze and report duplicates without removing them'
    )
    parser.add_argument(
        '--clean', 
        action='store_true',
        help='Remove duplicate articles from the database'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        default=True,
        help='Show what would be deleted without actually deleting (default: True)'
    )
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Actually perform the cleanup (overrides --dry-run)'
    )
    
    args = parser.parse_args()
    
    # Show help if no arguments provided
    if not args.analyze and not args.clean:
        parser.print_help()
        return
    
    print("🔍 PostgreSQL Duplicate News Article Handler")
    print("=" * 50)
    
    # Initialize database manager
    try:
        db_manager = DatabaseManager()
        print(f"✅ Connected to database: {Config.DB_TYPE}")
        
        if Config.DB_TYPE == 'sqlite':
            print("ℹ️  Note: You're using SQLite. This script is designed for PostgreSQL duplicate issues.")
            print("   SQLite typically doesn't have the same duplicate problems.")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    # Initialize deduplicator
    deduplicator = NewsDeduplicator()
    
    if args.analyze:
        print("\n📊 Analyzing duplicate patterns...")
        deduplicator.analyze_duplicate_patterns()
        
        # Get duplicate statistics
        print("\n🔍 Running duplicate detection...")
        stats = deduplicator.remove_duplicate_articles(dry_run=True)
        
        print(f"\n📈 Duplicate Analysis Results:")
        print(f"   Total articles in database: {stats['total_articles']}")
        print(f"   URL-based duplicates: {stats['url_duplicates']}")
        print(f"   Content-based duplicates: {stats['content_duplicates']}")
        print(f"   Total duplicates found: {stats['removed_articles']}")
        
        if stats['removed_articles'] > 0:
            print(f"\n💡 To remove these duplicates, run:")
            print(f"   python cleanup_duplicates.py --clean --force")
        else:
            print(f"\n✅ No duplicates found! Your database is clean.")
    
    elif args.clean:
        dry_run = args.dry_run and not args.force
        
        if dry_run:
            print("\n🔍 DRY RUN MODE: Analyzing what would be removed...")
        else:
            print("\n🧹 CLEANUP MODE: Removing duplicate articles...")
        
        stats = deduplicator.remove_duplicate_articles(dry_run=dry_run)
        
        print(f"\n📊 Cleanup Results:")
        print(f"   Total articles processed: {stats['total_articles']}")
        print(f"   URL duplicates found: {stats['url_duplicates']}")
        print(f"   Content duplicates found: {stats['content_duplicates']}")
        print(f"   Articles {'would be' if dry_run else 'were'} removed: {stats['removed_articles']}")
        
        if dry_run and stats['removed_articles'] > 0:
            print(f"\n💡 To actually remove these duplicates, run:")
            print(f"   python cleanup_duplicates.py --clean --force")
        elif not dry_run:
            print(f"\n✅ Database cleanup completed!")
    
    print("\n🔄 Future Duplicate Prevention:")
    print("   The updated database.py now includes duplicate detection")
    print("   when saving new articles, so this issue should not recur.")
    print("   The dashboard.py also filters duplicates when displaying articles.")

if __name__ == "__main__":
    main()
