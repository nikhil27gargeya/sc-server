import os
import smartcar
from smartcar import exceptions
from flask import Flask, request, redirect, session, render_template, jsonify
from dotenv import load_dotenv
import hmac
import hashlib
from datetime import datetime, timezone
import json

# Import database models
from models import db, User, Vehicle, WebhookData, UserSession

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY environment variable is required")

# Database configuration - PostgreSQL only
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

# Render provides DATABASE_URL for PostgreSQL
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Validate Smartcar configuration
smartcar_client_id = os.getenv('SMARTCAR_CLIENT_ID')
smartcar_client_secret = os.getenv('SMARTCAR_CLIENT_SECRET')
smartcar_redirect_uri = os.getenv('SMARTCAR_REDIRECT_URI')

if not smartcar_client_id or not smartcar_client_secret or not smartcar_redirect_uri:
    raise ValueError("SMARTCAR_CLIENT_ID, SMARTCAR_CLIENT_SECRET, and SMARTCAR_REDIRECT_URI environment variables are required")

client = smartcar.AuthClient(
    client_id=smartcar_client_id,
    client_secret=smartcar_client_secret,
    redirect_uri=smartcar_redirect_uri,
    test_mode=False
)

# Database helper functions
def store_access_token(vehicle_id, access_token_data):
    """Store access token in database"""
    try:
        # Parse expiration time
        from datetime import datetime, timezone
        expiration = datetime.fromtimestamp(access_token_data['expiration'], tz=timezone.utc)
        
        # Check if vehicle exists
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if vehicle:
            # Update existing vehicle
            vehicle.access_token = access_token_data['access_token']
            vehicle.refresh_token = access_token_data['refresh_token']
            vehicle.token_expires_at = expiration
            vehicle.updated_at = datetime.utcnow()
        else:
            # Get or create default user
            default_user = User.query.filter_by(smartcar_user_id='default_user').first()
            if not default_user:
                default_user = User(
                    smartcar_user_id='default_user',
                    email='default@example.com'
                )
                db.session.add(default_user)
                db.session.flush()  # Get the ID
            
            # Create new vehicle
            vehicle = Vehicle(
                smartcar_vehicle_id=vehicle_id,
                access_token=access_token_data['access_token'],
                refresh_token=access_token_data['refresh_token'],
                token_expires_at=expiration,
                user_id=default_user.id
            )
            db.session.add(vehicle)
        
        db.session.commit()
        print(f"Stored access token for vehicle {vehicle_id}")
        return True
    except Exception as e:
        print(f"Error storing access token: {str(e)}")
        db.session.rollback()
        return False

def get_access_token(vehicle_id):
    """Get access token from database"""
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if vehicle:
            # Check if token is expired
            from datetime import datetime, timezone
            if vehicle.token_expires_at > datetime.now(timezone.utc):
                return {
                    'access_token': vehicle.access_token,
                    'refresh_token': vehicle.refresh_token,
                    'expiration': vehicle.token_expires_at.timestamp()
                }
            else:
                # Token expired, try to refresh
                return refresh_access_token_db(vehicle.refresh_token, vehicle_id)
        return None
    except Exception as e:
        print(f"Error getting access token: {str(e)}")
        return None

def refresh_access_token_db(refresh_token, vehicle_id):
    """Refresh access token and update database"""
    try:
        new_token = client.refresh_token(refresh_token)
        if new_token:
            store_access_token(vehicle_id, new_token)
            return new_token
        return None
    except Exception as e:
        print(f"Error refreshing token in database: {str(e)}")
        return None

def store_webhook_data(vehicle_id, event_type, data, raw_data=None, timestamp=None):
    """Store webhook data in database"""
    try:
        if timestamp is None:
            timestamp = datetime.now()
        
        # Find vehicle by smartcar_vehicle_id
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if not vehicle:
            print(f"Vehicle {vehicle_id} not found in database")
            return False
        
        webhook_entry = WebhookData(
            vehicle_id=vehicle.id,
            event_type=event_type,
            timestamp=timestamp,
            data=json.dumps(data),
            raw_data=json.dumps(raw_data) if raw_data else None
        )
        
        db.session.add(webhook_entry)
        db.session.commit()
        print(f"Stored webhook data for vehicle {vehicle_id}, event {event_type}")
        return True
    except Exception as e:
        print(f"Error storing webhook data: {str(e)}")
        db.session.rollback()
        return False

def get_webhook_data(vehicle_id=None, event_type=None, limit=100):
    """Get webhook data from database"""
    try:
        query = WebhookData.query
        
        if vehicle_id:
            vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
            if vehicle:
                query = query.filter_by(vehicle_id=vehicle.id)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        entries = query.order_by(WebhookData.timestamp.desc()).limit(limit).all()
        return [entry.to_dict() for entry in entries]
    except Exception as e:
        print(f"Error getting webhook data: {str(e)}")
        return []

def get_latest_webhook_data(vehicle_id, event_type):
    """Get latest webhook data for specific vehicle and event type"""
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if not vehicle:
            return None
        
        entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type=event_type
        ).order_by(WebhookData.timestamp.desc()).first()
        
        return entry.to_dict() if entry else None
    except Exception as e:
        print(f"Error getting latest webhook data: {str(e)}")
        return None

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

# Database-only token management - no session fallback

@app.route('/exchange')
def exchange():
    code = request.args.get('code')
    
    if not code:
        content = '<div class="error">Authorization code not found in request</div>'
        return render_template('base.html', content=content)
    
    try:
        access_token = client.exchange_code(code)
        
        print(f"Received access token: {access_token}")
        
        # Store in database only - no session storage
        print(f"Storing token in database only")
        
        # Get vehicle info to store in database
        try:
            vehicle_ids = smartcar.get_vehicle_ids(access_token['access_token'])
            if vehicle_ids['vehicles']:
                vehicle_id = vehicle_ids['vehicles'][0]
                
                # Get vehicle details
                vehicle = smartcar.Vehicle(vehicle_id, access_token['access_token'])
                vehicle_info = vehicle.info()
                
                # Store token in database
                store_access_token(vehicle_id, access_token)
                
                # Update vehicle info in database
                db_vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
                if db_vehicle:
                    db_vehicle.make = vehicle_info.get('make')
                    db_vehicle.model = vehicle_info.get('model')
                    db_vehicle.year = vehicle_info.get('year')
                    db.session.commit()
                    print(f"Updated vehicle info for {vehicle_id}")
                
        except Exception as e:
            print(f"Error storing vehicle info in database: {str(e)}")
        
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
        # First try to get token from database
        db_vehicles = Vehicle.query.all()
        access_token = None
        vehicle_id = None
        
        if db_vehicles:
            # Use the first vehicle in database
            db_vehicle = db_vehicles[0]
            vehicle_id = db_vehicle.smartcar_vehicle_id
            token_data = get_access_token(vehicle_id)
            if token_data:
                access_token = token_data['access_token']
                print(f"Using database token for vehicle {vehicle_id}")
        
        # No fallback - require database tokens
        if not access_token:
            content = '''
            <div class="error">
                <h3>No Vehicle Connected</h3>
                <p>No vehicles found in database. Please connect a vehicle first.</p>
                <a href="/login" class="btn">Connect Vehicle</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        print(f"Session keys: {list(session.keys())}")
        
        if not access_token or not vehicle_id:
            content = '''
            <div class="error">
                <h3>Authentication Required</h3>
                <p>Your access token has expired or is invalid. Please reconnect your vehicle.</p>
                <a href="/login" class="btn">Reconnect</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        print(f"Using access token: {access_token}")
        print(f"Using vehicle ID: {vehicle_id}")
        
        vehicle = smartcar.Vehicle(vehicle_id, access_token)
        
        print("Getting vehicle info...")
        info = vehicle.info()
        print(f"Vehicle info: {info}")
        
        # --- Location ---
        location_from_webhook = get_latest_webhook_data(vehicle_id, 'Location.PreciseLocation')
        
        if location_from_webhook:
            location_data = location_from_webhook['data']
            lat = location_data.get('latitude', 'N/A')
            lng = location_data.get('longitude', 'N/A')
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
        odometer_from_webhook = get_latest_webhook_data(vehicle_id, 'Odometer.TraveledDistance')
        
        if odometer_from_webhook:
            odometer_data = odometer_from_webhook['data']
            distance = odometer_data.get('distance', odometer_data.get('value', 'N/A'))
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
        soc_from_webhook = get_latest_webhook_data(vehicle_id, 'TractionBattery.StateOfCharge')
        if soc_from_webhook:
            soc_data = soc_from_webhook['data']
            soc_value = soc_data.get('percentage', soc_data.get('value', 'N/A'))
            soc_info = f"<p><strong>State of Charge:</strong> {soc_value}% (from webhook)</p>"
        else:
            soc_info = "<p><strong>State of Charge:</strong> N/A</p>"
        
        # --- TractionBattery.NominalCapacity ---
        capacity_from_webhook = get_latest_webhook_data(vehicle_id, 'TractionBattery.NominalCapacity')
        if capacity_from_webhook:
            capacity_data = capacity_from_webhook['data']
            capacity_value = capacity_data.get('capacity', 'N/A')
            capacity_info = f"<p><strong>Nominal Capacity:</strong> {capacity_value} kWh (from webhook)</p>"
        else:
            capacity_info = "<p><strong>Nominal Capacity:</strong> N/A</p>"
        
        # --- Charge.ChargeLimits or Charge.ChargeLimitConfiguration ---
        charge_limits_from_webhook = get_latest_webhook_data(vehicle_id, 'Charge.ChargeLimits')
        if charge_limits_from_webhook:
            charge_limits_data = charge_limits_from_webhook['data']
            charge_limits_info = f"<p><strong>Charge Limits:</strong> {charge_limits_data} (from webhook)</p>"
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
                    store_webhook_data(vehicle_id, "Location.PreciseLocation", loc, raw_data=data)

                # Odometer.TraveledDistance
                odo = signals.get("odometer", {}).get("traveledDistance")
                if odo:
                    store_webhook_data(vehicle_id, "Odometer.TraveledDistance", odo, raw_data=data)

                # TractionBattery.StateOfCharge
                soc = signals.get("tractionBattery", {}).get("stateOfCharge")
                if soc:
                    store_webhook_data(vehicle_id, "TractionBattery.StateOfCharge", soc, raw_data=data)

                # TractionBattery.NominalCapacity
                cap = signals.get("tractionBattery", {}).get("nominalCapacity")
                if cap:
                    store_webhook_data(vehicle_id, "TractionBattery.NominalCapacity", cap, raw_data=data)

                # Charge.ChargeLimits or Charge.ChargeLimitConfiguration
                charge_limits = signals.get("charge", {}).get("chargeLimits")
                if charge_limits:
                    store_webhook_data(vehicle_id, "Charge.ChargeLimits", charge_limits, raw_data=data)

            # Database automatically handles storage, no need to limit entries

            return {'status': 'success', 'message': 'Batch payload processed'}, 200

        # Fallback: handle as individual event (existing logic)
        # Check if this is a verification request
        if data.get('eventName') == 'verify':
            return handle_verification(data)
        
        # Store the webhook data with timestamp
        vehicle_id = data.get('vehicleId')
        event_type = data.get('eventType')
        event_data = data.get('data', {})
        
        # Store in database
        store_webhook_data(vehicle_id, event_type, event_data, raw_data=data)
        
        print(f"Stored individual webhook data for vehicle {vehicle_id}, event {event_type}")
        
        # Log the webhook for debugging
        print(f"Vehicle ID: {vehicle_id}")
        print(f"Event Type: {event_type}")
        
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
        import json
        # Get webhook data from database
        webhook_entries = get_webhook_data(limit=50)
        
        # Create HTML for webhook entries
        webhook_entries_html = ""
        for entry in webhook_entries:  # Already ordered by newest first
            try:
                data_str = json.dumps(entry.get('data', {}), indent=2)
            except Exception:
                data_str = str(entry.get('data', {}))
            
            # Get vehicle info
            vehicle = Vehicle.query.get(entry.get('vehicle_id'))
            vehicle_id_display = vehicle.smartcar_vehicle_id if vehicle else 'Unknown'
            
            webhook_entries_html += f'''
            <div class="webhook-entry" style="border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px;">
                <h4>Event: {entry.get('event_type', 'N/A')}</h4>
                <p><strong>Vehicle ID:</strong> {vehicle_id_display}</p>
                <p><strong>Timestamp:</strong> {entry.get('timestamp', 'N/A')}</p>
                <p><strong>Data:</strong></p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">{data_str}</pre>
            </div>
            '''

        if not webhook_entries:
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
    latest_location = get_latest_webhook_data(vehicle_id, 'Location.PreciseLocation')
    
    if not latest_location:
        return {'error': 'No location data found for this vehicle'}, 404
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_location['timestamp'],
        'location': latest_location['data']
    }

@app.route('/api/vehicle/<vehicle_id>/battery')
def get_vehicle_battery(vehicle_id):
    """Get battery data for a specific vehicle"""
    soc_data = get_latest_webhook_data(vehicle_id, 'TractionBattery.StateOfCharge')
    capacity_data = get_latest_webhook_data(vehicle_id, 'TractionBattery.NominalCapacity')
    
    if not soc_data and not capacity_data:
        return {'error': 'No battery data found for this vehicle'}, 404
    
    battery_data = {}
    latest_timestamp = None
    
    if soc_data:
        battery_data['state_of_charge'] = soc_data['data']
        latest_timestamp = soc_data['timestamp']
    
    if capacity_data:
        battery_data['nominal_capacity'] = capacity_data['data']
        if not latest_timestamp or capacity_data['timestamp'] > latest_timestamp:
            latest_timestamp = capacity_data['timestamp']
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': latest_timestamp,
        'battery': battery_data
    }

@app.route('/api/vehicle/<vehicle_id>/battery/state-of-charge')
def get_vehicle_battery_state_of_charge(vehicle_id):
    """Get battery state of charge for a specific vehicle"""
    soc_data = get_latest_webhook_data(vehicle_id, 'TractionBattery.StateOfCharge')
    
    if not soc_data:
        return {'error': 'No battery state of charge data found for this vehicle'}, 404
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': soc_data['timestamp'],
        'state_of_charge': soc_data['data']
    }

@app.route('/api/vehicle/<vehicle_id>/battery/capacity')
def get_vehicle_battery_capacity(vehicle_id):
    """Get battery nominal capacity for a specific vehicle"""
    capacity_data = get_latest_webhook_data(vehicle_id, 'TractionBattery.NominalCapacity')
    
    if not capacity_data:
        return {'error': 'No battery capacity data found for this vehicle'}, 404
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': capacity_data['timestamp'],
        'nominal_capacity': capacity_data['data']
    }

@app.route('/api/vehicle/<vehicle_id>/odometer')
def get_vehicle_odometer(vehicle_id):
    """Get odometer data for a specific vehicle"""
    odometer_data = get_latest_webhook_data(vehicle_id, 'Odometer.TraveledDistance')
    
    if not odometer_data:
        return {'error': 'No odometer data found for this vehicle'}, 404
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': odometer_data['timestamp'],
        'odometer': odometer_data['data']
    }

@app.route('/api/vehicle/<vehicle_id>/charge-limits')
def get_vehicle_charge_limits(vehicle_id):
    """Get charge limits data for a specific vehicle"""
    charge_data = get_latest_webhook_data(vehicle_id, 'Charge.ChargeLimits')
    
    if not charge_data:
        return {'error': 'No charge limits data found for this vehicle'}, 404
    
    return {
        'vehicle_id': vehicle_id,
        'timestamp': charge_data['timestamp'],
        'charge_limits': charge_data['data']
    }

@app.route('/api/vehicle/<vehicle_id>/all')
def get_all_vehicle_data(vehicle_id):
    vehicle_entries = get_webhook_data(vehicle_id=vehicle_id)
    
    if not vehicle_entries:
        return {'error': 'No data found for this vehicle'}, 404
    
    vehicle_data = {
        'vehicle_id': vehicle_id,
        'last_updated': vehicle_entries[0]['timestamp'] if vehicle_entries else None,
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
    vehicles = Vehicle.query.all()
    vehicle_ids = [vehicle.smartcar_vehicle_id for vehicle in vehicles]
    
    # Get total webhook entries
    total_entries = WebhookData.query.count()
    
    return {
        'vehicles': vehicle_ids,
        'total_vehicles': len(vehicle_ids),
        'total_entries': total_entries
    }

@app.route('/api/vehicle/<vehicle_id>/latest-signals')
def get_latest_signals(vehicle_id):
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
        latest_entry = get_latest_webhook_data(vehicle_id, event_type)
        if latest_entry:
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
        
        if not challenge:
            print("Error: No challenge found in verification request")
            return {'error': 'No challenge provided'}, 400
        
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
    # Find the latest batch entry for this vehicle
    vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
    if not vehicle:
        return {'error': 'Vehicle not found'}, 404
    
    latest_batch = WebhookData.query.filter_by(
        vehicle_id=vehicle.id
    ).order_by(WebhookData.timestamp.desc()).first()
    
    if latest_batch and 'signals' in latest_batch.data_dict:
        return extract_signals_from_entry(latest_batch.to_dict())
    
    return {'error': 'No batch signal data found for this vehicle'}, 404

@app.route('/clear-webhook-data', methods=['POST'])
def clear_webhook_data():
    try:
        # Clear all webhook data from database
        WebhookData.query.delete()
        db.session.commit()
        return {'status': 'success', 'message': 'All webhook data cleared from database'}, 200
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500