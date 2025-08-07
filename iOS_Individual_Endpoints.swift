import Foundation
import UIKit

// MARK: - Individual Signal Response Models
struct LocationResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let location: LocationData
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp, location
    }
}

struct LocationData: Codable {
    let latitude: Double
    let longitude: Double
    let direction: String?
    let heading: Double?
    let locationType: String?
}

struct OdometerResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let odometer: OdometerData
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp, odometer
    }
}

struct OdometerData: Codable {
    let value: Int
}

struct StateOfChargeResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let stateOfCharge: Int
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp
        case stateOfCharge = "state_of_charge"
    }
}

struct NominalCapacityResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let nominalCapacity: Int
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp
        case nominalCapacity = "nominal_capacity"
    }
}

struct ChargeLimitsResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let chargeLimit: Int
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp
        case chargeLimit = "charge_limit"
    }
}

// MARK: - Updated SmartcarService with Individual Endpoints
class SmartcarService {
    private let baseURL = "https://sc-server-o0m5.onrender.com"
    private let session = URLSession.shared
    
    // MARK: - OAuth Flow
    func initiateOAuth(userId: String) -> URL? {
        guard let url = URL(string: "\(baseURL)/login?user_id=\(userId)") else {
            return nil
        }
        return url
    }
    
    // MARK: - Individual Signal Endpoints
    
    func fetchVehicleLocation(userId: String, vehicleId: String) async throws -> LocationResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/location") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(LocationResponse.self, from: data)
    }
    
    func fetchVehicleOdometer(userId: String, vehicleId: String) async throws -> OdometerResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/odometer") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(OdometerResponse.self, from: data)
    }
    
    func fetchVehicleStateOfCharge(userId: String, vehicleId: String) async throws -> StateOfChargeResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/state-of-charge") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(StateOfChargeResponse.self, from: data)
    }
    
    func fetchVehicleNominalCapacity(userId: String, vehicleId: String) async throws -> NominalCapacityResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/nominal-capacity") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(NominalCapacityResponse.self, from: data)
    }
    
    func fetchVehicleChargeLimits(userId: String, vehicleId: String) async throws -> ChargeLimitsResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/charge-limits") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(ChargeLimitsResponse.self, from: data)
    }
    
    // MARK: - Vehicle List (for getting available vehicles)
    func fetchUserVehicles(userId: String) async throws -> VehicleResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicles") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(VehicleResponse.self, from: data)
    }
}

// MARK: - Vehicle Models (from previous example)
struct Vehicle: Codable {
    let smartcarVehicleId: String
    let make: String?
    let model: String?
    let year: Int?
    
    enum CodingKeys: String, CodingKey {
        case smartcarVehicleId = "smartcar_vehicle_id"
        case make, model, year
    }
}

struct VehicleResponse: Codable {
    let userId: String
    let vehicles: [Vehicle]
    let totalVehicles: Int
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicles
        case totalVehicles = "total_vehicles"
    }
}

// MARK: - View Controller Example with Individual Endpoints
class VehicleDetailViewController: UIViewController {
    private let smartcarService = SmartcarService()
    private let userId = "ios_user_12345"
    private let vehicleId = "31581c01-3f29-4906-a194-9c150d456ea8"
    
    @IBOutlet weak var locationLabel: UILabel!
    @IBOutlet weak var odometerLabel: UILabel!
    @IBOutlet weak var batteryLabel: UILabel!
    @IBOutlet weak var capacityLabel: UILabel!
    @IBOutlet weak var chargeLimitLabel: UILabel!
    @IBOutlet weak var refreshButton: UIButton!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        loadAllVehicleData()
    }
    
    private func setupUI() {
        title = "Vehicle Details"
        refreshButton.addTarget(self, action: #selector(refreshData), for: .touchUpInside)
    }
    
    @objc private func refreshData() {
        loadAllVehicleData()
    }
    
    private func loadAllVehicleData() {
        Task {
            await loadLocationData()
            await loadOdometerData()
            await loadBatteryData()
            await loadCapacityData()
            await loadChargeLimitData()
        }
    }
    
    // MARK: - Individual Data Loading Methods
    
    private func loadLocationData() async {
        do {
            let response = try await smartcarService.fetchVehicleLocation(userId: userId, vehicleId: vehicleId)
            
            await MainActor.run {
                let location = response.location
                self.locationLabel.text = "📍 \(location.latitude), \(location.longitude)\nType: \(location.locationType ?? "Unknown")"
            }
        } catch {
            await MainActor.run {
                self.locationLabel.text = "📍 Location: Error loading data"
            }
        }
    }
    
    private func loadOdometerData() async {
        do {
            let response = try await smartcarService.fetchVehicleOdometer(userId: userId, vehicleId: vehicleId)
            
            await MainActor.run {
                let distance = response.odometer.value
                self.odometerLabel.text = "🛣️ Distance: \(distance) km"
            }
        } catch {
            await MainActor.run {
                self.odometerLabel.text = "🛣️ Odometer: Error loading data"
            }
        }
    }
    
    private func loadBatteryData() async {
        do {
            let response = try await smartcarService.fetchVehicleStateOfCharge(userId: userId, vehicleId: vehicleId)
            
            await MainActor.run {
                let soc = response.stateOfCharge
                self.batteryLabel.text = "🔋 Battery: \(soc)%"
            }
        } catch {
            await MainActor.run {
                self.batteryLabel.text = "🔋 Battery: Error loading data"
            }
        }
    }
    
    private func loadCapacityData() async {
        do {
            let response = try await smartcarService.fetchVehicleNominalCapacity(userId: userId, vehicleId: vehicleId)
            
            await MainActor.run {
                let capacity = response.nominalCapacity
                self.capacityLabel.text = "⚡ Capacity: \(capacity) kWh"
            }
        } catch {
            await MainActor.run {
                self.capacityLabel.text = "⚡ Capacity: Error loading data"
            }
        }
    }
    
    private func loadChargeLimitData() async {
        do {
            let response = try await smartcarService.fetchVehicleChargeLimits(userId: userId, vehicleId: vehicleId)
            
            await MainActor.run {
                let limit = response.chargeLimit
                self.chargeLimitLabel.text = "🔌 Charge Limit: \(limit)%"
            }
        } catch {
            await MainActor.run {
                self.chargeLimitLabel.text = "🔌 Charge Limit: Error loading data"
            }
        }
    }
}

// MARK: - Usage Examples

/*
 
 // Example 1: Get just the battery level
 let batteryLevel = try await smartcarService.fetchVehicleStateOfCharge(
     userId: "user_123", 
     vehicleId: "vehicle_456"
 )
 print("Battery: \(batteryLevel.stateOfCharge)%")
 
 // Example 2: Get just the location
 let location = try await smartcarService.fetchVehicleLocation(
     userId: "user_123", 
     vehicleId: "vehicle_456"
 )
 print("Location: \(location.location.latitude), \(location.location.longitude)")
 
 // Example 3: Get just the odometer
 let odometer = try await smartcarService.fetchVehicleOdometer(
     userId: "user_123", 
     vehicleId: "vehicle_456"
 )
 print("Distance: \(odometer.odometer.value) km")
 
 // Example 4: Get just the charge limit
 let chargeLimit = try await smartcarService.fetchVehicleChargeLimits(
     userId: "user_123", 
     vehicleId: "vehicle_456"
 )
 print("Charge Limit: \(chargeLimit.chargeLimit)%")
 
 // Example 5: Get just the nominal capacity
 let capacity = try await smartcarService.fetchVehicleNominalCapacity(
     userId: "user_123", 
     vehicleId: "vehicle_456"
 )
 print("Capacity: \(capacity.nominalCapacity) kWh")
 
 */

// MARK: - Benefits of Individual Endpoints

/*
 
 ✅ Benefits for iOS App:
 
 1. **Clean Data**: Each endpoint returns exactly what you need
 2. **Type Safety**: Strongly typed responses for each signal
 3. **Performance**: Only fetch the data you need
 4. **Error Handling**: Specific error messages for each signal
 5. **Caching**: Cache individual signals separately
 6. **UI Updates**: Update specific UI elements independently
 
 Example UI Update:
 
 // Update only the battery indicator
 Task {
     let battery = try await smartcarService.fetchVehicleStateOfCharge(userId: userId, vehicleId: vehicleId)
     batteryIndicator.text = "\(battery.stateOfCharge)%"
 }
 
 // Update only the location
 Task {
     let location = try await smartcarService.fetchVehicleLocation(userId: userId, vehicleId: vehicleId)
     mapView.centerOn(location.location.latitude, location.location.longitude)
 }
 
 */ 