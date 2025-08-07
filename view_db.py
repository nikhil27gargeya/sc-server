#!/usr/bin/env python3
"""
Database Viewer Script for Smartcar Server
Connect to your Render PostgreSQL database and view tokens, vehicles, and webhook data
"""

import os
import psycopg2
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

def connect_to_database():
    """Connect to the Render PostgreSQL database"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("error ")
            return None
        
        print(f"🔗 Connecting to database...")
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"error 2")
        return None

def view_users(conn):
    """View all users in the database"""
    print("\n👥 USERS TABLE:")
    print("=" * 50)
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, smartcar_user_id, email, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    
    if not users:
        print("No users found")
        return
    
    for user in users:
        print(f"ID: {user[0]}")
        print(f"Smartcar User ID: {user[1]}")
        print(f"Email: {user[2]}")
        print(f"Created: {user[3]}")
        print("-" * 30)

def view_vehicles(conn):
    """View all vehicles and their tokens"""
    print("\n🚗 VEHICLES TABLE:")
    print("=" * 50)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.id, v.smartcar_vehicle_id, v.make, v.model, v.year, 
               v.access_token, v.refresh_token, v.token_expires_at, v.created_at,
               u.smartcar_user_id
        FROM vehicles v
        LEFT JOIN users u ON v.user_id = u.id
        ORDER BY v.created_at DESC
    """)
    vehicles = cursor.fetchall()
    
    if not vehicles:
        print("No vehicles found")
        return
    
    for vehicle in vehicles:
        print(f"Vehicle ID: {vehicle[0]}")
        print(f"Smartcar Vehicle ID: {vehicle[1]}")
        print(f"Make: {vehicle[2]}")
        print(f"Model: {vehicle[3]}")
        print(f"Year: {vehicle[4]}")
        print(f"User: {vehicle[9]}")
        print(f"Access Token: {vehicle[5][:20]}..." if vehicle[5] else "No access token")
        print(f"Refresh Token: {vehicle[6][:20]}..." if vehicle[6] else "No refresh token")
        print(f"Token Expires: {vehicle[7]}")
        print(f"Created: {vehicle[8]}")
        print("-" * 50)

def view_webhook_data(conn, limit=10):
    """View recent webhook data"""
    print(f"\n📡 WEBHOOK DATA (Latest {limit} entries):")
    print("=" * 50)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.id, w.event_type, w.timestamp, w.data, w.raw_data,
               v.smartcar_vehicle_id
        FROM webhook_data w
        LEFT JOIN vehicles v ON w.vehicle_id = v.id
        ORDER BY w.timestamp DESC
        LIMIT %s
    """, (limit,))
    
    webhooks = cursor.fetchall()
    
    if not webhooks:
        print("No webhook data found")
        return
    
    for webhook in webhooks:
        print(f"ID: {webhook[0]}")
        print(f"Event Type: {webhook[1]}")
        print(f"Vehicle ID: {webhook[5]}")
        print(f"Timestamp: {webhook[2]}")
        
        # Try to parse and display data
        try:
            data = json.loads(webhook[3]) if webhook[3] else {}
            print(f"Data: {json.dumps(data, indent=2)}")
        except:
            print(f"Data: {webhook[3][:100]}..." if webhook[3] else "No data")
        
        print("-" * 30)

def view_database_stats(conn):
    """View database statistics"""
    print("\n📊 DATABASE STATISTICS:")
    print("=" * 50)
    
    cursor = conn.cursor()
    
    # Count users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    # Count vehicles
    cursor.execute("SELECT COUNT(*) FROM vehicles")
    vehicle_count = cursor.fetchone()[0]
    
    # Count webhook entries
    cursor.execute("SELECT COUNT(*) FROM webhook_data")
    webhook_count = cursor.fetchone()[0]
    
    # Count by event type
    cursor.execute("""
        SELECT event_type, COUNT(*) 
        FROM webhook_data 
        GROUP BY event_type 
        ORDER BY COUNT(*) DESC
    """)
    event_counts = cursor.fetchall()
    
    print(f"Users: {user_count}")
    print(f"Vehicles: {vehicle_count}")
    print(f"Webhook Entries: {webhook_count}")
    print("\nWebhook Events by Type:")
    for event_type, count in event_counts:
        print(f"  {event_type}: {count}")

def main():
    """Main function to view database contents"""
    print("🔍 Smartcar Database Viewer")
    print("=" * 50)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        # View database statistics
        view_database_stats(conn)
        
        # View users
        view_users(conn)
        
        # View vehicles and tokens
        view_vehicles(conn)
        
        # View recent webhook data
        view_webhook_data(conn, limit=5)
        
        print("\n✅ Database viewing complete!")
        
    except Exception as e:
        print(f"❌ Error viewing database: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 