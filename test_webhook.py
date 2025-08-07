#!/usr/bin/env python3
"""
Test script to simulate webhook payload to the Smartcar server
"""

import requests
import json

# Webhook payload from the user
webhook_payload = {
  "eventId": "d9829604-8fb2-49b7-9f02-4fd5b440d526",
  "eventType": "VEHICLE_STATE",
  "data": {
    "user": {
      "id": "0d02902c-cf38-414c-9fc0-5bd99fbb8d28"
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
          "latitude": 51.5014,
          "longitude": -0.1419,
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
          "value": 78
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
  },
  "triggers": [],
  "meta": {
    "version": "4.0",
    "webhookId": "06ef6008-b2c4-4583-8610-484e3ee2d613",
    "webhookName": "ChargePointWH",
    "deliveryId": "003a8f51-a06f-4d26-ab46-49dc286b7d55",
    "deliveredAt": "2025-08-06T23:35:45.450Z",
    "mode": "TEST",
    "signalCount": 5
  }
}

def test_webhook():
    """Test the webhook endpoint with the payload"""
    
    # Your Render app URL
    webhook_url = "https://sc-server-o0m5.onrender.com/webhook"
    
    print("🚀 Testing webhook endpoint...")
    print(f"📡 URL: {webhook_url}")
    print(f"📦 Payload size: {len(json.dumps(webhook_payload))} characters")
    print(f"🚗 Vehicle ID: {webhook_payload['data']['vehicle']['id']}")
    print(f"📊 Signal count: {webhook_payload['meta']['signalCount']}")
    print("-" * 50)
    
    try:
        # Send POST request to webhook endpoint
        response = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"✅ Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("🎉 Webhook processed successfully!")
            try:
                response_data = response.json()
                print(f"📋 Response Data: {json.dumps(response_data, indent=2)}")
            except:
                print(f"📋 Response Text: {response.text}")
        else:
            print(f"❌ Webhook failed with status {response.status_code}")
            print(f"📋 Error Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_latest_signals():
    """Test the latest-signals endpoint"""
    
    vehicle_id = webhook_payload['data']['vehicle']['id']
    signals_url = f"https://sc-server-o0m5.onrender.com/api/vehicle/{vehicle_id}/latest-signals"
    
    print("\n🔍 Testing latest-signals endpoint...")
    print(f"📡 URL: {signals_url}")
    print(f"🚗 Vehicle ID: {vehicle_id}")
    print("-" * 50)
    
    try:
        response = requests.get(signals_url, timeout=30)
        
        print(f"✅ Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("🎉 Latest signals retrieved successfully!")
            try:
                signals_data = response.json()
                print(f"📊 Signals Data:")
                for signal_type, data in signals_data.items():
                    if data:
                        print(f"  {signal_type}: {json.dumps(data, indent=4)}")
                    else:
                        print(f"  {signal_type}: No data")
            except:
                print(f"📋 Response Text: {response.text}")
        else:
            print(f"❌ Latest signals failed with status {response.status_code}")
            print(f"📋 Error Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    # Test webhook endpoint
    test_webhook()
    
    # Wait a moment for processing
    import time
    print("\n⏳ Waiting 3 seconds for database processing...")
    time.sleep(3)
    
    # Test latest signals endpoint
    test_latest_signals() 