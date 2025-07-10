import os
import smartcar
from smartcar import exceptions
from flask import Flask, request, redirect, session, render_template
from dotenv import load_dotenv
import hmac
import hashlib
from datetime import datetime

# Global variable to store webhook data
webhook_data_store = []

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

client = smartcar.AuthClient(
    client_id=os.getenv('SMARTCAR_CLIENT_ID'),
    client_secret=os.getenv('SMARTCAR_CLIENT_SECRET'),
    redirect_uri=os.getenv('SMARTCAR_REDIRECT_URI'),
    scope=['read_vehicle_info', 'read_odometer', 'read_location'],
    test_mode=True
)

@app.route('/')
def index():
    content = """
    <h2>Smartcar Demo</h2>
    <a href="/login" class="btn">Connect Your Vehicle</a>
    <a href="/vehicle" class="btn">View Vehicle Info</a>
    <a href="/webhook-data" class="btn">Webhook Dashboard</a>
    """
    return render_template('base.html', content=content)

@app.route('/login')
def login():
    auth_url = client.get_auth_url()
    return redirect(auth_url)

@app.route('/exchange')
def exchange():
    code = request.args.get('code')
    
    if not code:
        content = '<div class="error">Authorization code not found in request</div>'
        return render_template('base.html', content=content)
    
    try:
        access_token = client.exchange_code(code)
        
        print(f"Received access token: {access_token}")
        
        session['access_token'] = access_token['access_token']
        print(f"Stored access token in session: {session.get('access_token')}")
        
        content = '''
        <div class="success">
            <h3>Authentication Successful!</h3>
            <p>Your vehicle has been connected successfully.</p>
            <a href="/vehicle" class="btn">View Vehicle Information</a>
        </div>
        '''
        return render_template('base.html', content=content)
        
    except Exception as e:
        content = f'<div class="error">Error exchanging code: {str(e)}</div>'
        return render_template('base.html', content=content)

@app.route('/vehicle')
def vehicle():
    try:
        access_token_data = session.get('access_token')
        
        print(f"Session access_token: {access_token_data}")
        print(f"Session keys: {list(session.keys())}")
        
        if not access_token_data:
            content = '''
            <div class="error">
                <h3>No Access Token Found</h3>
                <p>Please authenticate your vehicle first.</p>
                <a href="/login" class="btn">Connect Your Vehicle</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        # Extract the access token string from the token object
        if isinstance(access_token_data, dict):
            access_token = access_token_data.get('access_token')
        else:
            access_token = access_token_data
            
        if not access_token:
            content = '''
            <div class="error">
                <h3>Invalid Access Token</h3>
                <p>Please authenticate your vehicle first.</p>
                <a href="/login" class="btn">Connect Your Vehicle</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        print(f"Using access token: {access_token}")
        
        print("Getting vehicle IDs...")
        vehicle_ids = smartcar.get_vehicle_ids(access_token)
        print(f"Vehicle IDs response: {vehicle_ids}")
        
        if not vehicle_ids['vehicles']:
            content = '<div class="error">No vehicles found for this user</div>'
            return render_template('base.html', content=content)
        
        vehicle_id = vehicle_ids['vehicles'][0]
        print(f"Using vehicle ID: {vehicle_id}")
        
        vehicle = smartcar.Vehicle(vehicle_id, access_token)
        
        print("Getting vehicle info...")
        info = vehicle.info()
        print(f"Vehicle info: {info}")
        
        location_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and entry.get('event_type') == 'Location.PreciseLocation':
                location_from_webhook = entry.get('data', {})
                break
        
        if location_from_webhook:
            lat = location_from_webhook.get('latitude', 'N/A')
            lng = location_from_webhook.get('longitude', 'N/A')
            location_info = f"<p><strong>Location:</strong> {lat}, {lng} (from webhook)</p>"
        else:
            try:
                print("Getting vehicle location...")
                location = vehicle.location()
                print(f"Location response: {location}")
                location_info = f"<p><strong>Location:</strong> {location.get('data', {}).get('latitude', 'N/A')}, {location.get('data', {}).get('longitude', 'N/A')} (from API)</p>"
            except smartcar.exceptions.RateLimitingException as e:
                print(f"Rate limiting error: {str(e)}")
                location_info = f"<p><strong>Location:</strong> Rate limited - please try again later</p>"
            except Exception as e:
                print(f"Error getting location: {str(e)}")
                location_info = "<p><strong>Location:</strong> Error retrieving location</p>"
        
        odometer_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and entry.get('event_type') == 'Odometer.TraveledDistance':
                odometer_from_webhook = entry.get('data', {})
                break
        
        if odometer_from_webhook:
            distance = odometer_from_webhook.get('distance', 'N/A')
            odometer_info = f"<p><strong>Odometer:</strong> {distance} km (from webhook)</p>"
        else:
            try:
                print("Getting vehicle odometer...")
                odometer = vehicle.odometer()
                print(f"Odometer response: {odometer}")
                odometer_info = f"<p><strong>Odometer:</strong> {odometer.get('data', {}).get('distance', 'N/A')} km (from API)</p>"
            except smartcar.exceptions.RateLimitingException as e:
                print(f"Rate limiting error: {str(e)}")
                odometer_info = f"<p><strong>Odometer:</strong> Rate limited - please try again later</p>"
            except Exception as e:
                print(f"Error getting odometer: {str(e)}")
                odometer_info = "<p><strong>Odometer:</strong> Error retrieving odometer</p>"
        
        content = f'''
        <h2>Vehicle Information</h2>
        <div class="info">
            <h3>Basic Info</h3>
            <p><strong>Make:</strong> {info['make']}</p>
            <p><strong>Model:</strong> {info['model']}</p>
            <p><strong>Year:</strong> {info['year']}</p>
            <p><strong>ID:</strong> {vehicle_id}</p>
        </div>
        
        <div class="info">
            <h3>Location</h3>
            {location_info}
        </div>
        
        <div class="info">
            <h3>Odometer</h3>
            {odometer_info}
        </div>
        
        <a href="/" class="btn">Back to Home</a>
        '''
        
        return render_template('base.html', content=content)
        
    except smartcar.exceptions.RateLimitingException as e:
        print(f"Rate limiting error: {str(e)}")
        content = f'''
        <div class="error">
            <h3>Rate Limiting Error</h3>
            <p>You have reached the throttling rate limit for this vehicle. Please try again later.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/vehicle" class="btn">Try Again</a>
        </div>
        '''
        return render_template('base.html', content=content)
    except smartcar.exceptions.AuthenticationException as e:
        print(f"Authentication error: {str(e)}")
        content = f'''
        <div class="error">
            <h3>Authentication Error</h3>
            <p>There was an authentication error. Please reconnect your vehicle.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/login" class="btn">Reconnect Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)
    except smartcar.exceptions.PermissionException as e:
        print(f"Permission error: {str(e)}")
        content = f'''
        <div class="error">
            <h3>Permission Error</h3>
            <p>You don't have permission to access this vehicle data.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/login" class="btn">Reconnect Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        content = f'''
        <div class="error">
            <h3>Unexpected Error</h3>
            <p>An unexpected error occurred while retrieving vehicle information.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/vehicle" class="btn">Try Again</a>
        </div>
        '''
        return render_template('base.html', content=content)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get the webhook data
        data = request.get_json()
        
        print(f"Received webhook data: {data}")
        
        # Check if this is a verification request
        if data.get('eventName') == 'verify':
            return handle_verification(data)
        
        # Store the webhook data with timestamp
        webhook_entry = {
            'timestamp': datetime.now().isoformat(),
            'vehicle_id': data.get('vehicleId'),
            'event_type': data.get('eventType'),
            'data': data.get('data', {}),
            'raw_data': data
        }
        
        # Add to global store (keep last 100 entries)
        global webhook_data_store
        webhook_data_store.append(webhook_entry)
        if len(webhook_data_store) > 100:
            webhook_data_store = webhook_data_store[-100:]
        
        print(f"Stored webhook data. Total entries: {len(webhook_data_store)}")
        
        # Process the webhook data
        vehicle_id = data.get('vehicleId')
        event_type = data.get('eventType')
        timestamp = data.get('timestamp')
        
        # Log the webhook for debugging
        print(f"Vehicle ID: {vehicle_id}")
        print(f"Event Type: {event_type}")
        print(f"Timestamp: {timestamp}")
        
        # Handle different event types
        if event_type == 'vehicle.location':
            location_data = data.get('data', {})
            print(f"Location update: {location_data}")
            
        elif event_type == 'vehicle.odometer':
            odometer_data = data.get('data', {})
            print(f"Odometer update: {odometer_data}")
            
        elif event_type == 'vehicle.error':
            error_data = data.get('data', {})
            print(f"Vehicle error: {error_data}")
            # Handle vehicle errors (connection issues, etc.)
            
        elif event_type == 'vehicle.disconnect':
            print(f"Vehicle disconnected: {vehicle_id}")
            # Handle vehicle disconnection
            
        # Handle specific data signals
        elif event_type == 'Charge.ChargeLimits':
            charge_limits = data.get('data', {})
            print(f"Charge limits update: {charge_limits}")
            
        elif event_type == 'Location.PreciseLocation':
            precise_location = data.get('data', {})
            print(f"Precise location update: {precise_location}")
            
        elif event_type == 'Odometer.TraveledDistance':
            traveled_distance = data.get('data', {})
            print(f"Traveled distance update: {traveled_distance}")
            
        elif event_type == 'TractionBattery.StateOfCharge':
            battery_soc = data.get('data', {})
            print(f"Battery state of charge update: {battery_soc}")
            
        elif event_type == 'TractionBattery.NominalCapacity':
            battery_capacity = data.get('data', {})
            print(f"Battery nominal capacity update: {battery_capacity}")
            
        else:
            print(f"Unknown event type: {event_type}")
        
        # Return success response
        return {'status': 'success'}, 200
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/webhook-data')
def webhook_data():
    """Display webhook data dashboard"""
    try:
        global webhook_data_store
        import json
        # Create HTML for webhook entries
        webhook_entries_html = ""
        for entry in reversed(webhook_data_store):  # Show newest first
            try:
                data_str = json.dumps(entry.get('data', {}), indent=2)
            except Exception:
                data_str = str(entry.get('data', {}))
            webhook_entries_html += f'''
            <div class="webhook-entry" style="border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px;">
                <h4>Event: {entry.get('event_type', 'N/A')}</h4>
                <p><strong>Vehicle ID:</strong> {entry.get('vehicle_id', 'N/A')}</p>
                <p><strong>Timestamp:</strong> {entry.get('timestamp', 'N/A')}</p>
                <p><strong>Data:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">{data_str}</pre>
            </div>
            '''

        if not webhook_data_store:
            webhook_entries_html = '<p style="color: #666;">No webhook data received yet. Send some test requests to see data here.</p>'

        content = f'''
        <h2>Webhook Data Dashboard</h2>
        <div class="info">
            <h3>Tracked Data Signals</h3>
            <ul>
                <li><strong>Charge.ChargeLimits:</strong> Battery charging limits</li>
                <li><strong>Location.PreciseLocation:</strong> Vehicle GPS coordinates</li>
                <li><strong>Odometer.TraveledDistance:</strong> Total distance traveled</li>
                <li><strong>TractionBattery.StateOfCharge:</strong> Current battery percentage</li>
                <li><strong>TractionBattery.NominalCapacity:</strong> Battery capacity</li>
            </ul>
        </div>
        <div class="info">
            <h3>API Endpoints for Developers</h3>
            <p>Your developer team can use these endpoints to get vehicle data:</p>
            <ul>
                <li><strong>Get Vehicle Location:</strong> <code>GET /api/vehicle/{'{vehicle_id}'}/location</code></li>
                <li><strong>Get Vehicle Battery:</strong> <code>GET /api/vehicle/{'{vehicle_id}'}/battery</code></li>
                <li><strong>Get Vehicle Odometer:</strong> <code>GET /api/vehicle/{'{vehicle_id}'}/odometer</code></li>
                <li><strong>Get Vehicle Charge Limits:</strong> <code>GET /api/vehicle/{'{vehicle_id}'}/charge-limits</code></li>
                <li><strong>Get All Vehicle Data:</strong> <code>GET /api/vehicle/{'{vehicle_id}'}/all</code></li>
                <li><strong>Get All Vehicles:</strong> <code>GET /api/vehicles</code></li>
            </ul>
            <h4>Example Usage:</h4>
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">
# Get location of your simulated vehicle
curl https://sc-server-o0m5.onrender.com/api/vehicle/a8d1ba1c-abb2-4e69-a637-a4be6/location
# Get all data for your vehicle
curl https://sc-server-o0m5.onrender.com/api/vehicle/a8d1ba1c-abb2-4e69-a637-a4be6/all
# Get list of all vehicles
curl https://sc-server-o0m5.onrender.com/api/vehicles
            </pre>
        </div>
        <div class="info">
            <h3>Webhook Endpoint</h3>
            <p><strong>URL:</strong> https://sc-server-o0m5.onrender.com/webhook</p>
            <p><strong>Method:</strong> POST</p>
            <p><strong>Content-Type:</strong> application/json</p>
            <p><strong>Total Entries Received:</strong> {len(webhook_data_store)}</p>
        </div>
        <div class="info">
            <h3>Received Webhook Data</h3>
            {webhook_entries_html}
        </div>
        <div class="info">
            <h3>Test Commands</h3>
            <p>Use these cURL commands to test your webhook:</p>
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">
# Location Test
curl -X POST https://sc-server-o0m5.onrender.com/webhook \
  -H "Content-Type: application/json" \
  -d '{{"vehicleId": "a8d1ba1c-abb2-4e69-a637-a4be6", "eventType": "Location.PreciseLocation", "data": {{"latitude": 37.7749, "longitude": -122.4194}}}}'
# Battery Test
curl -X POST https://sc-server-o0m5.onrender.com/webhook \
  -H "Content-Type: application/json" \
  -d '{{"vehicleId": "a8d1ba1c-abb2-4e69-a637-a4be6", "eventType": "TractionBattery.StateOfCharge", "data": {{"percentage": 75}}}}'
            </pre>
        </div>
        <a href="/" class="btn">Back to Home</a>
        '''
        return render_template('base.html', content=content)
    except Exception as e:
        print(f"Error in webhook_data route: {str(e)}")
        return f'<div class="error">Error loading webhook data: {str(e)}</div>', 500

@app.route('/api/vehicle/<vehicle_id>/location')
def get_vehicle_location(vehicle_id):
    """Get location data for a specific vehicle"""
    global webhook_data_store
    
    location_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] == 'Location.PreciseLocation'
    ]
    
    if not location_entries:
        return {'error': 'No location data found for this vehicle'}, 404
    
    latest_location = location_entries[-1]
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_location['timestamp'],
        'location': latest_location['data']
    }

@app.route('/api/vehicle/<vehicle_id>/battery')
def get_vehicle_battery(vehicle_id):
    """Get battery data for a specific vehicle"""
    global webhook_data_store
    
    battery_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] in ['TractionBattery.StateOfCharge', 'TractionBattery.NominalCapacity']
    ]
    
    if not battery_entries:
        return {'error': 'No battery data found for this vehicle'}, 404
    
    battery_data = {}
    for entry in battery_entries:
        if entry['event_type'] == 'TractionBattery.StateOfCharge':
            battery_data['state_of_charge'] = entry['data']
        elif entry['event_type'] == 'TractionBattery.NominalCapacity':
            battery_data['nominal_capacity'] = entry['data']
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': battery_entries[-1]['timestamp'],
        'battery': battery_data
    }

@app.route('/api/vehicle/<vehicle_id>/battery/state-of-charge')
def get_vehicle_battery_state_of_charge(vehicle_id):
    """Get battery state of charge for a specific vehicle"""
    global webhook_data_store
    
    soc_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] == 'TractionBattery.StateOfCharge'
    ]
    
    if not soc_entries:
        return {'error': 'No battery state of charge data found for this vehicle'}, 404
    
    latest_soc = soc_entries[-1]
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_soc['timestamp'],
        'state_of_charge': latest_soc['data']
    }

@app.route('/api/vehicle/<vehicle_id>/battery/capacity')
def get_vehicle_battery_capacity(vehicle_id):
    """Get battery nominal capacity for a specific vehicle"""
    global webhook_data_store
    
    capacity_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] == 'TractionBattery.NominalCapacity'
    ]
    
    if not capacity_entries:
        return {'error': 'No battery capacity data found for this vehicle'}, 404
    
    latest_capacity = capacity_entries[-1]
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_capacity['timestamp'],
        'nominal_capacity': latest_capacity['data']
    }

@app.route('/api/vehicle/<vehicle_id>/odometer')
def get_vehicle_odometer(vehicle_id):
    """Get odometer data for a specific vehicle"""
    global webhook_data_store
    
    odometer_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] == 'Odometer.TraveledDistance'
    ]
    
    if not odometer_entries:
        return {'error': 'No odometer data found for this vehicle'}, 404
    
    latest_odometer = odometer_entries[-1]
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_odometer['timestamp'],
        'odometer': latest_odometer['data']
    }

@app.route('/api/vehicle/<vehicle_id>/charge-limits')
def get_vehicle_charge_limits(vehicle_id):
    """Get charge limits data for a specific vehicle"""
    global webhook_data_store
    
    charge_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id and entry['event_type'] == 'Charge.ChargeLimits'
    ]
    
    if not charge_entries:
        return {'error': 'No charge limits data found for this vehicle'}, 404
    
    latest_charge = charge_entries[-1]
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_charge['timestamp'],
        'charge_limits': latest_charge['data']
    }

@app.route('/api/vehicle/<vehicle_id>/all')
def get_all_vehicle_data(vehicle_id):
    global webhook_data_store
    
    vehicle_entries = [
        entry for entry in webhook_data_store 
        if entry['vehicle_id'] == vehicle_id
    ]
    
    if not vehicle_entries:
        return {'error': 'No data found for this vehicle'}, 404
    
    vehicle_data = {
        'vehicle_id': vehicle_id,
        'last_updated': vehicle_entries[-1]['timestamp'],
        'data': {}
    }
    
    for entry in vehicle_entries:
        event_type = entry['event_type']
        if event_type not in vehicle_data['data']:
            vehicle_data['data'][event_type] = []
        vehicle_data['data'][event_type].append({
            'timestamp': entry['timestamp'],
            'data': entry['data']
        })
    
    return vehicle_data

@app.route('/api/vehicles')
def get_all_vehicles():
    global webhook_data_store
    
    vehicle_ids = list(set([entry['vehicle_id'] for entry in webhook_data_store]))
    
    return {
        'vehicles': vehicle_ids,
        'total_vehicles': len(vehicle_ids),
        'total_entries': len(webhook_data_store)
    }

def handle_verification(data):
    try:
        challenge = data.get('payload', {}).get('challenge')
        webhook_id = data.get('webhookId')
        
        print(f"Verification request for webhook ID: {webhook_id}")
        print(f"Challenge: {challenge}")
        
        management_token = os.getenv('SMARTCAR_MANAGEMENT_TOKEN')
        
        if not management_token:
            print("Error: SMARTCAR_MANAGEMENT_TOKEN not found in environment variables")
            return {'error': 'Management token not configured'}, 500
        
        hmac_hash = hmac.new(
            management_token.encode('utf-8'),
            challenge.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"Generated HMAC: {hmac_hash}")
        
        return {'challenge': hmac_hash}, 200
        
    except Exception as e:
        print(f"Error handling verification: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 