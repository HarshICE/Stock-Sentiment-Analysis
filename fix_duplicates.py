#!/usr/bin/env python3
"""
Script to fix duplicate articles in PostgreSQL database and add unique constraint
"""

from database import DatabaseManager, NewsArticle
from sqlalchemy import text
from datetime import datetime
import sys

def remove_duplicate_articles(db_manager):
    """Remove duplicate articles, keeping the oldest one for each URL"""
    print("🔍 Analyzing duplicate articles...")
    
    session = db_manager.get_session()
    try:
        # Find all URLs with duplicates
        duplicate_urls_query = text("""
            SELECT url, COUNT(*) as count 
            FROM news_articles 
            WHERE url IS NOT NULL 
            GROUP BY url 
            HAVING COUNT(*) > 1
        """)
        
        result = session.execute(duplicate_urls_query)
        duplicate_urls = result.fetchall()
        
        print(f"📊 Found {len(duplicate_urls)} URLs with duplicates")
        
        total_removed = 0
        
        for url, count in duplicate_urls:
            print(f"🔄 Processing URL with {count} duplicates...")
            
            # Get all articles for this URL, ordered by creation date (oldest first)
            articles = session.query(NewsArticle).filter(
                NewsArticle.url == url
            ).order_by(NewsArticle.created_at.asc()).all()
            
            # Keep the first (oldest) article, remove the rest
            if len(articles) > 1:
                articles_to_remove = articles[1:]  # All except the first
                
                print(f"  📝 Keeping oldest article: {articles[0].title[:50]}...")
                print(f"  🗑️  Removing {len(articles_to_remove)} duplicates")
                
                for article in articles_to_remove:
                    session.delete(article)
                    total_removed += 1
        
        # Commit the deletions
        session.commit()
        print(f"✅ Successfully removed {total_removed} duplicate articles")
        
        return total_removed
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error removing duplicates: {e}")
        return 0
    finally:
        session.close()

def add_unique_constraint(db_manager):
    """Add unique constraint to the url field"""
    print("🔧 Adding unique constraint to url field...")
    
    session = db_manager.get_session()
    try:
        # Check if constraint already exists
        check_constraint_query = text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'news_articles' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%url%'
        """)
        
        result = session.execute(check_constraint_query)
        existing_constraints = result.fetchall()
        
        if existing_constraints:
            print("ℹ️  Unique constraint on url already exists")
            return True
        
        # Add unique constraint
        alter_table_query = text("""
            ALTER TABLE news_articles 
            ADD CONSTRAINT news_articles_url_unique UNIQUE (url)
        """)
        
        session.execute(alter_table_query)
        session.commit()
        
        print("✅ Successfully added unique constraint to url field")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding unique constraint: {e}")
        return False
    finally:
        session.close()

def verify_fix(db_manager):
    """Verify that the fix worked"""
    print("🔍 Verifying the fix...")
    
    session = db_manager.get_session()
    try:
        # Check for remaining duplicates
        duplicate_check_query = text("""
            SELECT url, COUNT(*) as count 
            FROM news_articles 
            WHERE url IS NOT NULL 
            GROUP BY url 
            HAVING COUNT(*) > 1
        """)
        
        result = session.execute(duplicate_check_query)
        remaining_duplicates = result.fetchall()
        
        if remaining_duplicates:
            print(f"⚠️  Still found {len(remaining_duplicates)} duplicate URLs")
            return False
        else:
            print("✅ No duplicate URLs found")
        
        # Check constraint exists
        constraint_check_query = text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'news_articles' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%url%'
        """)
        
        result = session.execute(constraint_check_query)
        constraints = result.fetchall()
        
        if constraints:
            print("✅ Unique constraint is in place")
            return True
        else:
            print("❌ Unique constraint not found")
            return False
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    finally:
        session.close()

def main():
    """Main function to fix duplicates and add constraint"""
    print("🚀 Starting duplicate fix process...")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        
        # Step 1: Remove duplicate articles
        print("\n📝 Step 1: Removing duplicate articles")
        removed_count = remove_duplicate_articles(db_manager)
        
        if removed_count > 0:
            print(f"✅ Removed {removed_count} duplicate articles")
        else:
            print("ℹ️  No duplicates to remove")
        
        # Step 2: Add unique constraint
        print("\n🔧 Step 2: Adding unique constraint")
        constraint_added = add_unique_constraint(db_manager)
        
        if not constraint_added:
            print("❌ Failed to add unique constraint")
            sys.exit(1)
        
        # Step 3: Verify the fix
        print("\n✅ Step 3: Verifying the fix")
        if verify_fix(db_manager):
            print("\n🎉 SUCCESS! Duplicate issue has been fixed!")
            print("   - Duplicate articles removed")
            print("   - Unique constraint added to url field")
            print("   - Future duplicates will be prevented")
        else:
            print("\n❌ FAILED! Verification failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 Process completed successfully!")

if __name__ == "__main__":
    main()
