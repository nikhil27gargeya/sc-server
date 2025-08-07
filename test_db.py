#!/usr/bin/env python3
"""
Test script to verify database connection and functionality
"""

import os
from main import app, db
from models import User, Vehicle, WebhookData, UserSession

def test_database_connection():
    """Test database connection and basic operations"""
        with app.app_context():
        try:
            # Test basic query
            user_count = User.query.count()
            print(f"✅ Database connection successful! Found {user_count} users")
            
            # Test vehicle query
            vehicle_count = Vehicle.query.count()
            print(f"✅ Vehicle table accessible! Found {vehicle_count} vehicles")
            
            # Test webhook data query
            webhook_count = WebhookData.query.count()
            print(f"✅ Webhook data table accessible! Found {webhook_count} webhook entries")
            
            # Test creating a test entry
            test_user = User.query.filter_by(smartcar_user_id='test_user').first()
            if not test_user:
            test_user = User(
                    smartcar_user_id='test_user',
                email='test@example.com'
            )
            db.session.add(test_user)
            db.session.commit()
                print("✅ Successfully created test user")
            else:
                print("✅ Test user already exists")
            
            print("\n🎉 All database tests passed!")
            return True
            
    except Exception as e:
            print(f"❌ Database test failed: {str(e)}")
        return False

if __name__ == '__main__':
    test_database_connection() 