import Foundation
import UIKit

// MARK: - Data Models
struct Vehicle: Codable {
    let smartcarVehicleId: String
    let make: String?
    let model: String?
    let year: Int?
    let latestData: LatestData?
    
    enum CodingKeys: String, CodingKey {
        case smartcarVehicleId = "smartcar_vehicle_id"
        case make, model, year
        case latestData = "latest_data"
    }
}

struct LatestData: Codable {
    let location: LocationData?
    let battery: BatteryData?
    let odometer: OdometerData?
}

struct LocationData: Codable {
    let latitude: Double
    let longitude: Double
    let direction: String?
    let heading: Double?
    let locationType: String?
}

struct BatteryData: Codable {
    let value: Int
}

struct OdometerData: Codable {
    let value: Int
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

struct SignalsResponse: Codable {
    let userId: String
    let vehicleId: String
    let signals: [String: SignalData?]
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case signals
    }
}

struct SignalData: Codable {
    let timestamp: String
    let data: [String: AnyCodable]
}

// Helper for dynamic JSON
struct AnyCodable: Codable {
    let value: Any
    
    init(_ value: Any) {
        self.value = value
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dictionary = try? container.decode([String: AnyCodable].self) {
            value = dictionary.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch value {
        case let bool as Bool:
            try container.encode(bool)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let string as String:
            try container.encode(string)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dictionary as [String: Any]:
            try container.encode(dictionary.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
    }
}

// MARK: - SmartcarService
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
    
    // MARK: - Vehicle Data
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
    
    func fetchLatestSignals(userId: String, vehicleId: String) async throws -> SignalsResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/latest-signals") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(SignalsResponse.self, from: data)
    }
    
    func fetchVehicleLocation(userId: String, vehicleId: String) async throws -> LocationData {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/location") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        let locationResponse = try JSONDecoder().decode(LocationResponse.self, from: data)
        return locationResponse.location
    }
    
    func fetchVehicleBattery(userId: String, vehicleId: String) async throws -> BatteryResponse {
        guard let url = URL(string: "\(baseURL)/api/user/\(userId)/vehicle/\(vehicleId)/battery") else {
            throw URLError(.badURL)
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        
        return try JSONDecoder().decode(BatteryResponse.self, from: data)
    }
}

// MARK: - Response Models
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

struct BatteryResponse: Codable {
    let userId: String
    let vehicleId: String
    let timestamp: String
    let battery: [String: AnyCodable]
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case vehicleId = "vehicle_id"
        case timestamp, battery
    }
}

// MARK: - View Controller Example
class VehicleViewController: UIViewController {
    private let smartcarService = SmartcarService()
    private let userId = "ios_user_12345" // This would come from your app's user system
    
    @IBOutlet weak var tableView: UITableView!
    private var vehicles: [Vehicle] = []
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        loadVehicles()
    }
    
    private func setupUI() {
        title = "My Vehicles"
        navigationItem.rightBarButtonItem = UIBarButtonItem(
            barButtonSystemItem: .add,
            target: self,
            action: #selector(addVehicleTapped)
        )
    }
    
    @objc private func addVehicleTapped() {
        // Step 1: Initiate OAuth flow
        guard let oauthURL = smartcarService.initiateOAuth(userId: userId) else {
            showAlert(title: "Error", message: "Could not create OAuth URL")
            return
        }
        
        // Step 2: Open Safari for OAuth
        UIApplication.shared.open(oauthURL) { [weak self] success in
            if success {
                print("OAuth flow initiated")
                // In a real app, you'd handle the redirect back to your app
                // and then refresh the vehicle list
            } else {
                self?.showAlert(title: "Error", message: "Could not open OAuth URL")
            }
        }
    }
    
    private func loadVehicles() {
        Task {
            do {
                let response = try await smartcarService.fetchUserVehicles(userId: userId)
                
                await MainActor.run {
                    self.vehicles = response.vehicles
                    self.tableView.reloadData()
                }
            } catch {
                await MainActor.run {
                    self.showAlert(title: "Error", message: "Failed to load vehicles: \(error.localizedDescription)")
                }
            }
        }
    }
    
    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }
}

// MARK: - Table View Extension
extension VehicleViewController: UITableViewDataSource, UITableViewDelegate {
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return vehicles.count
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "VehicleCell", for: indexPath)
        let vehicle = vehicles[indexPath.row]
        
        cell.textLabel?.text = "\(vehicle.make ?? "Unknown") \(vehicle.model ?? "Vehicle")"
        cell.detailTextLabel?.text = "Battery: \(vehicle.latestData?.battery?.value ?? 0)%"
        
        return cell
    }
    
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        
        let vehicle = vehicles[indexPath.row]
        loadVehicleDetails(vehicle: vehicle)
    }
    
    private func loadVehicleDetails(vehicle: Vehicle) {
        Task {
            do {
                let signals = try await smartcarService.fetchLatestSignals(
                    userId: userId,
                    vehicleId: vehicle.smartcarVehicleId
                )
                
                await MainActor.run {
                    // Display vehicle details with signals
                    let alert = UIAlertController(
                        title: "\(vehicle.make ?? "") \(vehicle.model ?? "")",
                        message: "Latest data loaded successfully",
                        preferredStyle: .alert
                    )
                    alert.addAction(UIAlertAction(title: "OK", style: .default))
                    self.present(alert, animated: true)
                }
            } catch {
                await MainActor.run {
                    self.showAlert(title: "Error", message: "Failed to load vehicle details")
                }
            }
        }
    }
}

// MARK: - Usage Example
/*
 
 // In your iOS app:
 
 1. User opens your app and logs in
 2. Your app generates a unique user ID (or uses existing user ID)
 3. User taps "Connect Vehicle"
 4. Your app calls: smartcarService.initiateOAuth(userId: "user_123")
 5. Safari opens with Smartcar OAuth
 6. User completes OAuth and Smartcar redirects to your backend
 7. Backend stores tokens linked to user_123
 8. Your app polls: smartcarService.fetchUserVehicles(userId: "user_123")
 9. Your app displays vehicles and data for that specific user
 
 The key is that the user_id parameter links everything together!
 
 */ 