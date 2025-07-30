#!/bin/bash

# Database connection script for Smartcar Server
# This script connects to your Render PostgreSQL database using psql

# Load environment variables
source .env

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found in .env file"
    exit 1
fi

echo "🔗 Connecting to Render PostgreSQL database..."
echo "📊 Use these commands to explore your data:"
echo ""
echo "  \dt                    - List all tables"
echo "  SELECT * FROM users;   - View all users"
echo "  SELECT * FROM vehicles; - View all vehicles and tokens"
echo "  SELECT * FROM webhook_data ORDER BY timestamp DESC LIMIT 10; - View recent webhooks"
echo "  \q                     - Quit"
echo ""

# Connect to database
psql "$DATABASE_URL" 