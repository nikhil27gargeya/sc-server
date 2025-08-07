# Smartcar Server API Documentation

## Overview

This backend provides a complete user identification system for iOS apps to connect with Smartcar and retrieve vehicle data. The system stores OAuth tokens persistently in PostgreSQL and provides clean, individual endpoints for each vehicle signal.

## Base URL

```
https://sc-server-o0m5.onrender.com
```

## Complete User Flow

### 1. iOS App Initiates OAuth

**Endpoint:** `GET /login`

**Parameters:**
- `user_id` (required): Unique identifier for the iOS app user

**Example:**
```
GET /login?user_id=ios_user_12345
```

**Response:** Redirects to Smartcar OAuth page

### 2. Smartcar OAuth Completion

**Endpoint:** `GET /exchange`

**Parameters:**
- `code` (required): Authorization code from Smartcar
- `state` (required): Contains the user_id (passed through OAuth flow)

**Response:**
```json
{
  "status": "success",
  "message": "Vehicle connected successfully",
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8"
}
```

### 3. iOS App Polls for Data

After OAuth completion, the iOS app can poll individual endpoints to get vehicle data.

## Individual Signal Endpoints

### Location Data

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/location`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "timestamp": "2025-01-06T23:35:45.450Z",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "direction": "NE",
    "heading": 45.3,
    "locationType": "PARKED"
  }
}
```

### Odometer Data

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/odometer`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "timestamp": "2025-01-06T23:35:45.450Z",
  "odometer": {
    "value": 78432
  }
}
```

### Battery State of Charge

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/state-of-charge`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "timestamp": "2025-01-06T23:35:45.450Z",
  "state_of_charge": 85
}
```

### Battery Nominal Capacity

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/nominal-capacity`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "timestamp": "2025-01-06T23:35:45.450Z",
  "nominal_capacity": 75
}
```

### Charge Limits

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/charge-limits`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "timestamp": "2025-01-06T23:35:45.450Z",
  "charge_limit": 80
}
```

## Vehicle Management Endpoints

### Get User's Vehicles

**Endpoint:** `GET /api/user/{user_id}/vehicles`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicles": [
    {
      "smartcar_vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
      "make": "Tesla",
      "model": "Model 3",
      "year": 2020,
      "latest_data": {
        "location": {
          "latitude": 37.7749,
          "longitude": -122.4194
        },
        "battery": {
          "value": 85
        },
        "odometer": {
          "value": 78432
        }
      }
    }
  ],
  "total_vehicles": 1
}
```

### Get All Latest Signals (Combined)

**Endpoint:** `GET /api/user/{user_id}/vehicle/{vehicle_id}/latest-signals`

**Response:**
```json
{
  "user_id": "ios_user_12345",
  "vehicle_id": "31581c01-3f29-4906-a194-9c150d456ea8",
  "signals": {
    "Location.PreciseLocation": {
      "timestamp": "2025-01-06T23:35:45.450Z",
      "data": {
        "latitude": 37.7749,
        "longitude": -122.4194
      }
    },
    "TractionBattery.StateOfCharge": {
      "timestamp": "2025-01-06T23:35:45.450Z",
      "data": {
        "value": 85
      }
    }
  }
}
```

## Webhook Endpoint

### Receive Vehicle Data

**Endpoint:** `POST /webhook`

**Purpose:** Receives real-time vehicle data from Smartcar

**Supported Event Types:**
- `VEHICLE_STATE` (new format with signals array)
- `VehicleState` (legacy batch format)

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error description"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (missing parameters)
- `404`: Not Found (user/vehicle not found, no data available)
- `500`: Internal Server Error

## iOS App Integration Example

### Swift Code Example

```swift
class SmartcarService {
    private let baseURL = "https://sc-server-o0m5.onrender.com"
    
    // 1. Initiate OAuth
    func connectVehicle(userId: String) -> URL? {
        return URL(string: "\(baseURL)/login?user_id=\(userId)")
    }
    
    // 2. Get battery level
    func getBatteryLevel(userId: String, vehicleId: String) async throws -> Int {
        let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/state-of-charge")!
        let (data, _) = try await URLSession.shared.data(from: url)
        let response = try JSONDecoder().decode(StateOfChargeResponse.self, from: data)
        return response.stateOfCharge
    }
    
    // 3. Get location
    func getLocation(userId: String, vehicleId: String) async throws -> (lat: Double, lng: Double) {
        let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/location")!
        let (data, _) = try await URLSession.shared.data(from: url)
        let response = try JSONDecoder().decode(LocationResponse.self, from: data)
        return (response.location.latitude, response.location.longitude)
    }
}
```

## Data Flow Summary

1. **iOS App** calls `/login?user_id=YOUR_USER_ID`
2. **User** completes OAuth in Safari/WebView
3. **Smartcar** redirects to `/exchange` with code & state
4. **Backend** stores tokens linked to user_id in PostgreSQL
5. **iOS App** polls individual endpoints for specific data
6. **Backend** returns clean, single-value responses

## Security Features

- **User Verification**: All endpoints verify the vehicle belongs to the requesting user
- **Token Management**: Automatic token refresh when expired
- **Persistent Storage**: Tokens stored securely in PostgreSQL
- **Error Handling**: Comprehensive error responses for debugging

## Benefits for iOS Apps

1. **Clean Data**: Each endpoint returns exactly what you need
2. **Type Safety**: Strongly typed responses for each signal
3. **Performance**: Only fetch the data you need
4. **Error Handling**: Specific error messages for each signal
5. **Caching**: Cache individual signals separately
6. **UI Updates**: Update specific UI elements independently

## Testing

Use the provided test scripts:
- `test_individual_endpoints.py`: Test all individual endpoints
- `test_user_flow.py`: Test complete user identification flow
- `test_api_endpoints.py`: Comprehensive API testing

## Database Schema

The system uses PostgreSQL with the following tables:
- `users`: User information
- `vehicles`: Vehicle information and OAuth tokens
- `webhook_data`: Stored webhook payloads
- `user_sessions`: Session management (if needed) 