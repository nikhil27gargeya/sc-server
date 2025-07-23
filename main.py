import os
import smartcar
from smartcar import exceptions
from flask import Flask, request, redirect, session, render_template
from dotenv import load_dotenv
import hmac
import hashlib
from datetime import datetime

webhook_data_store = []

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

client = smartcar.AuthClient(
    client_id=os.getenv('SMARTCAR_CLIENT_ID'),
    client_secret=os.getenv('SMARTCAR_CLIENT_SECRET'),
    redirect_uri=os.getenv('SMARTCAR_REDIRECT_URI'),
    scope=['read_vehicle_info', 'read_odometer', 'read_location', 'read_battery', 'read_charge'],
    test_mode=True
)

@app.route('/')
def index():
    content = """
    <h2>Smartcar Server</h2>
    <a href="/login" class="btn">Smartcar Connect</a>
    <a href="/vehicle" class="btn">Vehicle Info</a>
    <a href="/webhook-data" class="btn">Webhook Info</a>
    """
    return render_template('base.html', content=content)

@app.route('/login')
def login():
    auth_url = client.get_auth_url()
    return redirect(auth_url)

def refresh_access_token(refresh_token):
    """Refresh the access token using the refresh token"""
    try:
        new_token = client.refresh_token(refresh_token)
        print(f"Token refreshed successfully: {new_token}")
        return new_token
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        return None

def is_token_expired(token_data):
    """Check if the access token is expired"""
    if not token_data or not isinstance(token_data, dict):
        return True
    
    expiration = token_data.get('expiration')
    if not expiration:
        return True
    
    # Add 5 minute buffer to refresh before actual expiration
    from datetime import datetime, timezone, timedelta
    buffer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    return expiration < buffer_time

def get_valid_access_token():
    """Get a valid access token, refreshing if necessary"""
    token_data = session.get('access_token')
    
    print(f"Current token data: {token_data}")
    
    if not token_data:
        print("No token data found in session")
        return None
    
    # If token_data is a string (old format), convert to dict
    if isinstance(token_data, str):
        print("Token is in old string format, cannot refresh")
        # We can't refresh without the full token object, so return None
        return None
    
    # Check if token is expired
    if is_token_expired(token_data):
        print("Token is expired, attempting to refresh...")
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            new_token = refresh_access_token(refresh_token)
            if new_token:
                session['access_token'] = new_token
                print("Token refreshed successfully")
                return new_token.get('access_token')
            else:
                # Refresh failed, clear session
                print("Token refresh failed, clearing session")
                session.pop('access_token', None)
                return None
        else:
            # No refresh token, clear session
            print("No refresh token available, clearing session")
            session.pop('access_token', None)
            return None
    
    print("Token is valid")
    return token_data.get('access_token')

@app.route('/exchange')
def exchange():
    code = request.args.get('code')
    
    if not code:
        content = '<div class="error">Authorization code not found in request</div>'
        return render_template('base.html', content=content)
    
    try:
        access_token = client.exchange_code(code)
        
        print(f"Received access token: {access_token}")
        
        session['access_token'] = access_token
        print(f"Stored full token object in session")
        
        content = '''
        <div class="success">
            <h3>Authentication Successful!</h3>
            <p>Your vehicle has been connected successfully.</p>
            <a href="/vehicle" class="btn">Vehicle Information</a>
        </div>
        '''
        return render_template('base.html', content=content)
        
    except Exception as e:
        content = f'<div class="error">Error exchanging code: {str(e)}</div>'
        return render_template('base.html', content=content)

@app.route('/vehicle')
def vehicle():
    try:
        # Get a valid access token (with automatic refresh if needed)
        access_token = get_valid_access_token()
        
        print(f"Session keys: {list(session.keys())}")
        
        if not access_token:
            content = '''
            <div class="error">
                <h3>Authentication Required</h3>
                <p>Your access token has expired or is invalid. Please reconnect your vehicle.</p>
                <a href="/login" class="btn">Reconnect</a>
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
        
        # --- Location ---
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
        
        # --- Odometer ---
        odometer_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and entry.get('event_type') == 'Odometer.TraveledDistance':
                odometer_from_webhook = entry.get('data', {})
                break
        
        if odometer_from_webhook:
            distance = odometer_from_webhook.get('distance', odometer_from_webhook.get('value', 'N/A'))
            odometer_info = f"<p><strong>Odometer:</strong> {distance} km (from webhook)</p>"
        else:
            try:
                print("Getting vehicle odometer...")
                odometer = vehicle.odometer()
                print(f"Odometer response: {odometer}")
                odometer_info = f"<p><strong>Odometer:</strong> {odometer.get('data', {}).get('distance', odometer.get('data', {}).get('value', 'N/A'))} km (from API)</p>"
            except smartcar.exceptions.RateLimitingException as e:
                print(f"Rate limiting error: {str(e)}")
                odometer_info = f"<p><strong>Odometer:</strong> Rate limited - please try again later</p>"
            except Exception as e:
                print(f"Error getting odometer: {str(e)}")
                odometer_info = "<p><strong>Odometer:</strong> Error retrieving odometer</p>"
        
        # --- TractionBattery.StateOfCharge ---
        soc_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and entry.get('event_type') == 'TractionBattery.StateOfCharge':
                soc_from_webhook = entry.get('data', {})
                break
        if soc_from_webhook:
            soc_value = soc_from_webhook.get('percentage', soc_from_webhook.get('value', 'N/A'))
            soc_info = f"<p><strong>State of Charge:</strong> {soc_value}% (from webhook)</p>"
        else:
            soc_info = "<p><strong>State of Charge:</strong> N/A</p>"
        
        # --- TractionBattery.NominalCapacity ---
        capacity_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and entry.get('event_type') == 'TractionBattery.NominalCapacity':
                capacity_from_webhook = entry.get('data', {})
                break
        if capacity_from_webhook:
            capacity_value = capacity_from_webhook.get('capacity', 'N/A')
            capacity_info = f"<p><strong>Nominal Capacity:</strong> {capacity_value} kWh (from webhook)</p>"
        else:
            capacity_info = "<p><strong>Nominal Capacity:</strong> N/A</p>"
        
        # --- Charge.ChargeLimits or Charge.ChargeLimitConfiguration ---
        charge_limits_from_webhook = None
        for entry in reversed(webhook_data_store):
            if entry.get('vehicle_id') == vehicle_id and (entry.get('event_type') == 'Charge.ChargeLimits' or entry.get('event_type') == 'Charge.ChargeLimitConfiguration'):
                charge_limits_from_webhook = entry.get('data', {})
                break
        if charge_limits_from_webhook:
            charge_limits_info = f"<p><strong>Charge Limits:</strong> {charge_limits_from_webhook} (from webhook)</p>"
        else:
            charge_limits_info = "<p><strong>Charge Limits:</strong> N/A</p>"
        
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
        <div class="info">
            <h3>State of Charge</h3>
            {soc_info}
        </div>
        <div class="info">
            <h3>Nominal Capacity</h3>
            {capacity_info}
        </div>
        <div class="info">
            <h3>Charge Limits</h3>
            {charge_limits_info}
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
        # Clear the invalid token from session
        session.pop('access_token', None)
        content = f'''
        <div class="error">
            <h3>Authentication Error</h3>
            <p>Access token has expired.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/login" class="btn">Reconnect</a>
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
    global webhook_data_store
    try:
        data = request.get_json()
        print(f"Received webhook data: {data}")

        # Check for batch payload (VehicleState type)
        if data.get("type") == "VehicleState" and "data" in data and "vehicles" in data["data"]:
            for vehicle in data["data"]["vehicles"]:
                vehicle_id = vehicle.get("vehicleId")
                signals = vehicle.get("signals", {})

                # Location.PreciseLocation
                loc = signals.get("location", {}).get("preciseLocation")
                if loc:
                    webhook_data_store.append({
                        "timestamp": data.get("deliveryTime"),
                        "vehicle_id": vehicle_id,
                        "event_type": "Location.PreciseLocation",
                        "data": loc,
                        "raw_data": data
                    })

                # Odometer.TraveledDistance
                odo = signals.get("odometer", {}).get("traveledDistance")
                if odo:
                    webhook_data_store.append({
                        "timestamp": data.get("deliveryTime"),
                        "vehicle_id": vehicle_id,
                        "event_type": "Odometer.TraveledDistance",
                        "data": odo,
                        "raw_data": data
                    })

                # TractionBattery.StateOfCharge
                soc = signals.get("tractionBattery", {}).get("stateOfCharge")
                if soc:
                    webhook_data_store.append({
                        "timestamp": data.get("deliveryTime"),
                        "vehicle_id": vehicle_id,
                        "event_type": "TractionBattery.StateOfCharge",
                        "data": soc,
                        "raw_data": data
                    })

                # TractionBattery.NominalCapacity
                cap = signals.get("tractionBattery", {}).get("nominalCapacity")
                if cap:
                    webhook_data_store.append({
                        "timestamp": data.get("deliveryTime"),
                        "vehicle_id": vehicle_id,
                        "event_type": "TractionBattery.NominalCapacity",
                        "data": cap,
                        "raw_data": data
                    })

                # Charge.ChargeLimits or Charge.ChargeLimitConfiguration
                charge_limits = signals.get("charge", {}).get("chargeLimits")
                if charge_limits:
                    webhook_data_store.append({
                        "timestamp": data.get("deliveryTime"),
                        "vehicle_id": vehicle_id,
                        "event_type": "Charge.ChargeLimits",
                        "data": charge_limits,
                        "raw_data": data
                    })

            # Keep only the last 100 entries
            if len(webhook_data_store) > 100:
                webhook_data_store = webhook_data_store[-100:]

            return {'status': 'success', 'message': 'Batch payload processed'}, 200

        # Fallback: handle as individual event (existing logic)
        # Get the webhook data
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
        <h2>Webhook Info</h2>
        <div class="info">
            <h3>5 Signals</h3>
            <ul>
                <li><strong>Charge.ChargeLimits:</strong> Battery charging limits</li>
                <li><strong>Location.PreciseLocation:</strong> Vehicle GPS coordinates</li>
                <li><strong>Odometer.TraveledDistance:</strong> Total distance traveled</li>
                <li><strong>TractionBattery.StateOfCharge:</strong> Current battery percentage</li>
                <li><strong>TractionBattery.NominalCapacity:</strong> Battery capacity</li>
            </ul>
        </div>
        <div class="info">
            <h3>Exposed REST API endpoints</h3>
            <ul>
                <li><strong>Get Vehicle Location:</strong> <code>GET /api/vehicle/vehicle_id/location</code></li>
                <li><strong>Get Vehicle Battery:</strong> <code>GET /api/vehicle/vehicle_id/battery</code></li>
                <li><strong>Get Vehicle Odometer:</strong> <code>GET /api/vehicle/vehicle_id/odometer</code></li>
                <li><strong>Get Vehicle Charge Limits:</strong> <code>GET /api/vehicle/vehicle_id/charge-limits</code></li>
                <li><strong>Get All Vehicle Data:</strong> <code>GET /api/vehicle/vehicle_id/all</code></li>
                <li><strong>Get All Vehicles:</strong> <code>GET /api/vehicles</code></li>
            </ul>
        <div class="info">
            <h3>Webhook Endpoint</h3>
            <p><strong>URL:</strong> https://sc-server-o0m5.onrender.com/webhook</p>
        </div>
        <a href="/" class="btn">Back</a>
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

@app.route('/api/vehicle/<vehicle_id>/latest-signals')
def get_latest_signals(vehicle_id):
    global webhook_data_store

    # Define the event types you want to fetch
    event_types = [
        'Location.PreciseLocation',
        'Odometer.TraveledDistance',
        'TractionBattery.StateOfCharge',
        'TractionBattery.NominalCapacity',
        'Charge.ChargeLimits'  # If you want Charge.ChargeLimitConfiguration, use that string
    ]

    latest_signals = {}

    for event_type in event_types:
        # Find the latest entry for this event type and vehicle
        entries = [
            entry for entry in webhook_data_store
            if entry['vehicle_id'] == vehicle_id and entry['event_type'] == event_type
        ]
        if entries:
            latest_entry = entries[-1]  # Assuming entries are in chronological order
            latest_signals[event_type] = {
                'timestamp': latest_entry['timestamp'],
                'data': latest_entry['data']
            }
        else:
            latest_signals[event_type] = None  # Or you can omit this key if preferred

    return latest_signals

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

def extract_signals_from_entry(entry):
    signals = entry['data'].get('signals', {})
    result = {}
    # Location
    if 'location' in signals and 'preciseLocation' in signals['location']:
        result['Location.PreciseLocation'] = [ { 'data': signals['location']['preciseLocation'] } ]
    # Odometer
    if 'odometer' in signals and 'traveledDistance' in signals['odometer']:
        result['Odometer.TraveledDistance'] = [ { 'data': signals['odometer']['traveledDistance'] } ]
    # State of Charge
    if 'tractionBattery' in signals and 'stateOfCharge' in signals['tractionBattery']:
        result['TractionBattery.StateOfCharge'] = [ { 'data': signals['tractionBattery']['stateOfCharge'] } ]
    # Nominal Capacity
    if 'tractionBattery' in signals and 'nominalCapacity' in signals['tractionBattery']:
        result['TractionBattery.NominalCapacity'] = [ { 'data': signals['tractionBattery']['nominalCapacity'] } ]
    # Charge Limits
    if 'charge' in signals and 'chargeLimits' in signals['charge']:
        result['Charge.ChargeLimits'] = [ { 'data': signals['charge']['chargeLimits'] } ]
    return result

@app.route('/api/vehicle/<vehicle_id>/signals-preview')
def signals_preview(vehicle_id):
    global webhook_data_store
    # Find the latest batch entry for this vehicle
    for entry in reversed(webhook_data_store):
        if entry['vehicle_id'] == vehicle_id and 'signals' in entry.get('data', {}):
            return extract_signals_from_entry(entry)
    return {'error': 'No batch signal data found for this vehicle'}, 404

@app.route('/clear-webhook-data', methods=['POST'])
def clear_webhook_data():
    global webhook_data_store
    webhook_data_store.clear()
    return {'status': 'success', 'message': 'webhook_data_store cleared'}, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 