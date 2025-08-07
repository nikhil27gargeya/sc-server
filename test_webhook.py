#!/usr/bin/env python3
"""
Test script to send a VEHICLE_STATE webhook payload to the server
"""

import requests
import json
from datetime import datetime

def test_webhook():
    # Test payload matching the new VEHICLE_STATE format
    webhook_payload = {
        "eventId": "test-event-123",
        "eventType": "VEHICLE_STATE",
        "data": {
            "user": {
                "id": "test-user-456"
            },
            "vehicle": {
                "id": "31581c01-3f29-4906-a194-9c150d456ea8",
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

if __name__ == "__main__":
    test_webhook() 