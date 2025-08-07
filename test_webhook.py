#!/usr/bin/env python3
"""
Test script to send a VEHICLE_STATE webhook payload to the server
"""

import requests
import json
from datetime import datetime

def test_webhook():
    # Test payload matching the new VEHICLE_STATE format with real user ID
    webhook_payload = {
        "eventId": "test-event-123",
        "eventType": "VEHICLE_STATE",
        "data": {
            "user": {
                "id": "test_user_100"  # Real user ID with connected vehicle
            },
            "vehicle": {
                "id": "31581c01-3f29-4906-a194-9c150d456ea8",  # Real vehicle ID from database
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
                        "direction": "NW",
                        "heading": 315.5,
                        "locationType": "PARKED"
                    },
                    "meta": {
                        "oemUpdatedAt": int(datetime.now().timestamp() * 1000),
                        "retrievedAt": int(datetime.now().timestamp() * 1000)
                    }
                },
                {
                    "code": "odometer-traveleddistance",
                    "name": "TraveledDistance",
                    "group": "Odometer",
                    "body": {
                        "value": 78500
                    },
                    "meta": {
                        "oemUpdatedAt": int(datetime.now().timestamp() * 1000),
                        "retrievedAt": int(datetime.now().timestamp() * 1000)
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
                        "oemUpdatedAt": int(datetime.now().timestamp() * 1000),
                        "retrievedAt": int(datetime.now().timestamp() * 1000)
                    }
                },
                {
                    "code": "tractionbattery-nominalcapacity",
                    "name": "NominalCapacity",
                    "group": "TractionBattery",
                    "body": {
                        "source": "SMARTCAR",
                        "capacity": 75,
                        "availbableCapacities": [
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
                        "oemUpdatedAt": int(datetime.now().timestamp() * 1000),
                        "retrievedAt": int(datetime.now().timestamp() * 1000)
                    }
                },
                {
                    "code": "charge-chargelimits",
                    "name": "ChargeLimits",
                    "group": "Charge",
                    "body": {
                        "values": {
                            "activeLimit": 90,
                            "values": [
                                {
                                    "type": "global",
                                    "limit": 90
                                },
                                {
                                    "type": "location",
                                    "condition": {
                                        "name": "Home",
                                        "address": "123 Test Street",
                                        "latitude": 37.7749,
                                        "longitude": -122.4194
                                    },
                                    "limit": 85
                                }
                            ]
                        }
                    },
                    "meta": {
                        "oemUpdatedAt": int(datetime.now().timestamp() * 1000),
                        "retrievedAt": int(datetime.now().timestamp() * 1000)
                    }
                }
            ]
        },
        "triggers": [],
        "meta": {
            "version": "4.0",
            "webhookId": "test-webhook-789",
            "webhookName": "TestWebhook",
            "deliveryId": "test-delivery-abc",
            "deliveredAt": datetime.now().isoformat() + "Z",
            "mode": "TEST",
            "signalCount": 5
        }
    }

    # Server URL (assuming running locally on port 5000)
    webhook_url = "http://localhost:5000/webhook"
    
    print("🚀 Testing webhook endpoint with new VEHICLE_STATE format...")
    print(f"📡 Sending payload to: {webhook_url}")
    print(f"📊 Payload size: {len(json.dumps(webhook_payload))} characters")
    
    try:
        # Send POST request to webhook endpoint
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"📋 Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"📋 Response Body: {response.text}")
            
        if response.status_code == 200:
            print("\n🎉 Webhook test successful!")
        else:
            print(f"\n❌ Webhook test failed with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Make sure the server is running on localhost:5000")
        print("💡 Start the server with: python3 main.py")
    except requests.exceptions.Timeout:
        print("\n❌ Timeout Error: Request took too long")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

def test_api_endpoints():
    """Test API endpoints for the real user test_user_100"""
    user_id = "test_user_100"
    vehicle_id = "31581c01-3f29-4906-a194-9c150d456ea8"
    base_url = "http://localhost:5000"
    
    print(f"\n🔍 Testing API endpoints for user: {user_id}")
    print(f"🚗 Vehicle ID: {vehicle_id}")
    print("=" * 60)
    
    # Test 1: Get user vehicles
    print("\n1️⃣ Testing /api/user/{user_id}/vehicles")
    try:
        response = requests.get(f"{base_url}/api/user/{user_id}/vehicles", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data.get('total_vehicles', 0)} vehicles")
            for vehicle in data.get('vehicles', []):
                print(f"   🚗 Vehicle: {vehicle.get('smartcar_vehicle_id')} - {vehicle.get('make')} {vehicle.get('model')}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    # Test 2: Get latest signals
    print("\n2️⃣ Testing /api/user/{user_id}/vehicle/{vehicle_id}/latest-signals")
    try:
        response = requests.get(f"{base_url}/api/user/{user_id}/vehicle/{vehicle_id}/latest-signals", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            signals = data.get('signals', {})
            print(f"   ✅ Found {len(signals)} signal types")
            for signal_type, signal_data in signals.items():
                if signal_data:
                    print(f"   📡 {signal_type}: {signal_data.get('timestamp', 'N/A')}")
                else:
                    print(f"   📡 {signal_type}: No data")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    # Test 3: Get location
    print("\n3️⃣ Testing /api/user/{user_id}/vehicle/{vehicle_id}/location")
    try:
        response = requests.get(f"{base_url}/api/user/{user_id}/vehicle/{vehicle_id}/location", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            location = data.get('location', {})
            print(f"   📍 Location: {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    # Test 4: Get battery state of charge
    print("\n4️⃣ Testing /api/user/{user_id}/vehicle/{vehicle_id}/state-of-charge")
    try:
        response = requests.get(f"{base_url}/api/user/{user_id}/vehicle/{vehicle_id}/state-of-charge", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            soc = data.get('state_of_charge', 'N/A')
            print(f"   🔋 Battery: {soc}%")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")

if __name__ == "__main__":
    test_webhook()
    print("\n" + "="*60)
    test_api_endpoints() 