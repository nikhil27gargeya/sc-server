#!/usr/bin/env python3
"""
Database initialization script for Smartcar Server
This script creates all necessary database tables
"""

import os
from dotenv import load_dotenv
from main import app, db
from models import User, Vehicle, WebhookData, UserSession

load_dotenv()

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("Database tables created successfully!")

        # Create a default user if none exists
        default_user = User.query.first()
        if not default_user:
            default_user = User(
                smartcar_user_id='default_user',
                email='default@example.com'
            )
            db.session.add(default_user)
            db.session.commit()
            print("Created default user")
        
        # Check table counts
        user_count = User.query.count()
        vehicle_count = Vehicle.query.count()
        webhook_count = WebhookData.query.count()
        session_count = UserSession.query.count()
        
        print(f"\nDatabase Status:")
        print(f"Users: {user_count}")
        print(f"Vehicles: {vehicle_count}")
        print(f"Webhook Data Entries: {webhook_count}")
        print(f"User Sessions: {session_count}")
        
        print("\nDatabase initialization complete!")

if __name__ == '__main__':
    init_database()