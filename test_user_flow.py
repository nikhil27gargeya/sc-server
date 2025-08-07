#!/usr/bin/env python3
"""
Test script to demonstrate the complete user identification flow
Simulates iOS app → Backend → Smartcar → Backend → iOS app
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://sc-server-o0m5.onrender.com"
TEST_USER_ID = "ios_user_12345"  # This would come from your iOS app
TEST_VEHICLE_ID = "31581c01-3f29-4906-a194-9c150d456ea8"  # From your test webhook

def test_complete_user_flow():
    """Test the complete flow from iOS app perspective"""
    
    print("🚗 Testing Complete User Identification Flow")
    print("=" * 50)
    
    # Step 1: iOS app initiates OAuth with user_id
    print("\n1️⃣ iOS App initiates OAuth with user_id...")
    login_url = f"{BASE_URL}/login?user_id={TEST_USER_ID}"
    print(f"   Login URL: {login_url}")
    
    # In real iOS app, this would open Safari/WebView
    # For testing, we'll simulate the redirect
    try:
        response = requests.get(login_url)
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print(f"   Error: {response.json()}")
            return False
        print("   ✅ Login initiated successfully")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    # Step 2: Simulate webhook data for the user's vehicle
    print("\n2️⃣ Simulating webhook data for user's vehicle...")
    webhook_payload = {
        "eventId": "d9829604-8fb2-49b7-9f02-4fd5b440d526",
        "eventType": "VEHICLE_STATE",
        "data": {
            "user": {
                "id": TEST_USER_ID  # This would be the actual Smartcar user ID
            },
            "vehicle": {
                "id": TEST_VEHICLE_ID,
                "make": "Tesla",
                "model": "Model 3",
                "year": 2020
            },
            "signals": [
                {
                    "code": "location-preciselocation",
                    "name": "PreciseLocation",
                    "group": "Location",
                    "body": {
                        "latitude": 37.7749,
                        "longitude": -122.4194,
                        "direction": "NE",
                        "heading": 45.3,
                        "locationType": "PARKED"
                    },
                    "meta": {
                        "oemUpdatedAt": 1754523345450,
                        "retrievedAt": 1754523345450
                    }
                },
                {
                    "code": "tractionbattery-stateofcharge",
                    "name": "StateOfCharge",
                    "group": "TractionBattery",
                    "body": {
                        "value": 85
                    },
                    "meta": {
                        "oemUpdatedAt": 1754523345450,
                        "retrievedAt": 1754523345450
                    }
                },
                {
                    "code": "odometer-traveleddistance",
                    "name": "TraveledDistance",
                    "group": "Odometer",
                    "body": {
                        "value": 78432
                    },
                    "meta": {
                        "oemUpdatedAt": 1754523345450,
                        "retrievedAt": 1754523345450
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook", json=webhook_payload)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Webhook data stored successfully")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 3: iOS app polls for user's vehicles
    print("\n3️⃣ iOS App polls for user's vehicles...")
    try:
        response = requests.get(f"{BASE_URL}/api/user/{TEST_USER_ID}/vehicles")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data['total_vehicles']} vehicles for user")
            for vehicle in data['vehicles']:
                print(f"      Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['smartcar_vehicle_id']})")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 4: iOS app gets latest signals for specific vehicle
    print("\n4️⃣ iOS App gets latest signals for vehicle...")
    try:
        response = requests.get(f"{BASE_URL}/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/latest-signals")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Latest signals retrieved:")
            for signal_type, signal_data in data['signals'].items():
                if signal_data:
                    print(f"      {signal_type}: {signal_data['data']}")
                else:
                    print(f"      {signal_type}: No data")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Step 5: iOS app gets specific data (location, battery)
    print("\n5️⃣ iOS App gets specific vehicle data...")
    
    # Get location
    try:
        response = requests.get(f"{BASE_URL}/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/location")
        print(f"   Location Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Location: {data['location']}")
        else:
            print(f"   ❌ Location Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Location Error: {str(e)}")
    
    # Get battery
    try:
        response = requests.get(f"{BASE_URL}/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/battery")
        print(f"   Battery Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Battery: {data['battery']}")
        else:
            print(f"   ❌ Battery Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Battery Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 User identification flow test completed!")
    print("\n📱 iOS App Integration Summary:")
    print("   1. iOS app calls: /login?user_id=YOUR_USER_ID")
    print("   2. User completes OAuth in Safari/WebView")
    print("   3. Smartcar redirects to: /exchange with code & state")
    print("   4. Backend stores tokens linked to user_id")
    print("   5. iOS app polls: /api/user/YOUR_USER_ID/vehicles")
    print("   6. iOS app gets data: /api/user/YOUR_USER_ID/vehicle/VEHICLE_ID/latest-signals")

if __name__ == "__main__":
    test_complete_user_flow() 