#!/usr/bin/env python3
"""
Database Viewer Script
Shows the contents of the webhook_data.db database in a readable format
"""

import sqlite3
import json
from datetime import datetime

def view_database():
    """View all webhook events in the database"""
    conn = sqlite3.connect('webhook_data.db')
    cursor = conn.cursor()
    
    print("=" * 80)
    print("WEBHOOK EVENTS DATABASE")
    print("=" * 80)
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM webhook_events")
    total_count = cursor.fetchone()[0]
    print(f"Total Events: {total_count}")
    
    # Get unique vehicles
    cursor.execute("SELECT DISTINCT vehicle_id FROM webhook_events")
    vehicles = [row[0] for row in cursor.fetchall()]
    print(f"Vehicles: {', '.join(vehicles)}")
    print()
    
    # Get all events ordered by timestamp
    cursor.execute("""
        SELECT id, vehicle_id, event_type, timestamp, processed_data, created_at 
        FROM webhook_events 
        ORDER BY timestamp DESC
    """)
    
    events = cursor.fetchall()
    
    if not events:
        print("No webhook events found in database.")
        return
    
    for i, event in enumerate(events, 1):
        event_id, vehicle_id, event_type, timestamp, processed_data, created_at = event
        
        print(f"Event #{i}")
        print(f"  ID: {event_id}")
        print(f"  Vehicle: {vehicle_id}")
        print(f"  Type: {event_type}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Created: {created_at}")
        
        # Parse and display processed data
        try:
            data = json.loads(processed_data)
            print(f"  Data: {json.dumps(data, indent=4)}")
        except json.JSONDecodeError:
            print(f"  Data: {processed_data}")
        
        print("-" * 40)
    
    conn.close()

def view_by_vehicle(vehicle_id):
    """View events for a specific vehicle"""
    conn = sqlite3.connect('webhook_data.db')
    cursor = conn.cursor()
    
    print(f"Events for vehicle: {vehicle_id}")
    print("=" * 50)
    
    cursor.execute("""
        SELECT event_type, timestamp, processed_data 
        FROM webhook_events 
        WHERE vehicle_id = ? 
        ORDER BY timestamp DESC
    """, (vehicle_id,))
    
    events = cursor.fetchall()
    
    if not events:
        print(f"No events found for vehicle {vehicle_id}")
        return
    
    for event_type, timestamp, processed_data in events:
        print(f"Type: {event_type}")
        print(f"Time: {timestamp}")
        try:
            data = json.loads(processed_data)
            print(f"Data: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError:
            print(f"Data: {processed_data}")
        print("-" * 30)
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        vehicle_id = sys.argv[1]
        view_by_vehicle(vehicle_id)
    else:
        view_database() 