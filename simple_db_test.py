#!/usr/bin/env python3
"""
Simple database connection test
"""

import os
import psycopg2
from psycopg2 import sql

def test_postgres_connection():
    """Test direct PostgreSQL connection"""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not set")
            return False
        
        print(f"🔗 Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        
        # Test if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"📋 Found tables: {table_names}")
        
        # Close connection
        cursor.close()
        conn.close()
        
        print("🎉 Database connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    test_postgres_connection() 