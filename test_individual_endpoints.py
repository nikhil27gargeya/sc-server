#!/usr/bin/env python3
"""
Test script to verify individual signal endpoints
Tests each endpoint separately for cleaner iOS app integration
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://sc-server-o0m5.onrender.com"
TEST_USER_ID = "ios_user_12345"
TEST_VEHICLE_ID = "31581c01-3f29-4906-a194-9c150d456ea8"

def test_individual_endpoints():
    """Test each individual signal endpoint"""
    
    print("🚗 Testing Individual Signal Endpoints")
    print("=" * 50)
    
    # Step 1: Send webhook data first
    print("\n1️⃣ Sending webhook data...")
    webhook_payload = {
        "eventId": "d9829604-8fb2-49b7-9f02-4fd5b440d526",
        "eventType": "VEHICLE_STATE",
        "data": {
            "user": {
                "id": TEST_USER_ID
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
                    "code": "tractionbattery-nominalcapacity",
                    "name": "NominalCapacity",
                    "group": "TractionBattery",
                    "body": {
                        "source": "SMARTCAR",
                        "capacity": 75,
                        "availableCapacities": [
                            {
                                "capacity": 55,
                                "description": "Standard Range"
                            },
                            {
                                "capacity": 75,
                                "description": "Long Range"
                            },
                            {
                                "capacity": 100,
                                "description": "Performance"
                            }
                        ]
                    },
                    "meta": {
                        "oemUpdatedAt": 1754523345450,
                        "retrievedAt": 1754523345450
                    }
                },
                {
                    "code": "charge-chargelimits",
                    "name": "ChargeLimits",
                    "group": "Charge",
                    "body": {
                        "values": {
                            "activeLimit": 80,
                            "values": [
                                {
                                    "type": "global",
                                    "limit": 80
                                },
                                {
                                    "type": "location",
                                    "condition": {
                                        "name": "Home",
                                        "address": "123 2nd street",
                                        "latitude": 90,
                                        "longitude": 90
                                    },
                                    "limit": 72
                                },
                                {
                                    "type": "connector",
                                    "condition": {
                                        "connectorType": "J1772"
                                    },
                                    "limit": 52
                                }
                            ]
                        }
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
            print("   ✅ Webhook data sent successfully")
        else:
            print(f"   ❌ Error: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return
    
    # Wait for processing
    print("\n⏳ Waiting 3 seconds for database processing...")
    time.sleep(3)
    
    # Step 2: Test each individual endpoint
    endpoints = [
        ("Location", f"/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/location"),
        ("Odometer", f"/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/odometer"),
        ("State of Charge", f"/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/state-of-charge"),
        ("Nominal Capacity", f"/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/nominal-capacity"),
        ("Charge Limits", f"/api/user/{TEST_USER_ID}/vehicle/{TEST_VEHICLE_ID}/charge-limits")
    ]
    
    print("\n2️⃣ Testing Individual Endpoints:")
    
    for name, endpoint in endpoints:
        print(f"\n   📍 Testing {name} endpoint...")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {name} data retrieved successfully")
                
                # Display the specific data
                if name == "Location":
                    location = data.get('location', {})
                    print(f"      Latitude: {location.get('latitude')}")
                    print(f"      Longitude: {location.get('longitude')}")
                    print(f"      Location Type: {location.get('locationType')}")
                
                elif name == "Odometer":
                    odometer = data.get('odometer', {})
                    print(f"      Distance: {odometer.get('value')} km")
                
                elif name == "State of Charge":
                    soc = data.get('state_of_charge')
                    print(f"      Battery: {soc}%")
                
                elif name == "Nominal Capacity":
                    capacity = data.get('nominal_capacity')
                    print(f"      Capacity: {capacity} kWh")
                
                elif name == "Charge Limits":
                    limit = data.get('charge_limit')
                    print(f"      Charge Limit: {limit}%")
                
                print(f"      Timestamp: {data.get('timestamp')}")
                
            else:
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Individual endpoint testing completed!")
    print("\n📱 iOS App Integration Summary:")
    print("   Individual endpoints for clean data access:")
    print("   • GET /api/user/{user_id}/vehicle/{vehicle_id}/location")
    print("   • GET /api/user/{user_id}/vehicle/{vehicle_id}/odometer")
    print("   • GET /api/user/{user_id}/vehicle/{vehicle_id}/state-of-charge")
    print("   • GET /api/user/{user_id}/vehicle/{vehicle_id}/nominal-capacity")
    print("   • GET /api/user/{user_id}/vehicle/{vehicle_id}/charge-limits")
    print("\n   Each endpoint returns:")
    print("   • Single value (no complex nested objects)")
    print("   • User verification (security)")
    print("   • Timestamp for data freshness")
    print("   • Clean JSON for easy iOS parsing")

if __name__ == "__main__":
    test_individual_endpoints() 