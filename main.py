import os
import smartcar
from flask import Flask, request, redirect, session, render_template, jsonify
from dotenv import load_dotenv
import hmac
import hashlib
from datetime import datetime, timezone
import json

from models import db, User, Vehicle, WebhookData, UserSession

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key:
    raise ValueError("SECRET_KEY env variable not found")

database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL env variable not found")

if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize database
db.init_app(app)

# smartcar configuration
smartcar_client_id = os.getenv('SMARTCAR_CLIENT_ID')
smartcar_client_secret = os.getenv('SMARTCAR_CLIENT_SECRET')
smartcar_redirect_uri = os.getenv('SMARTCAR_REDIRECT_URI')

if not smartcar_client_id or not smartcar_client_secret or not smartcar_redirect_uri:
    raise ValueError("smartcar env variables are required")

client = smartcar.AuthClient(
    client_id=smartcar_client_id,
    client_secret=smartcar_client_secret,
    redirect_uri=smartcar_redirect_uri,
    scope=['read_vehicle_info', 'read_location', 'read_odometer', 'read_battery', 'read_charge'],
    test_mode=False
)

#token management
def store_access_token(vehicle_id, access_token_data):
    try:
        from datetime import datetime, timezone
        # Handle both timestamp and datetime objects
        if isinstance(access_token_data['expiration'], (int, float)):
            expiration = datetime.fromtimestamp(access_token_data['expiration'], tz=timezone.utc)
        else:
            expiration = access_token_data['expiration']
        
        print(f"Starting store_access_token for vehicle {vehicle_id}")
        
        # Check if vehicle exists
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if vehicle:
            print(f"Found existing vehicle {vehicle_id}, updating tokens")
            vehicle.access_token = access_token_data['access_token']
            vehicle.refresh_token = access_token_data['refresh_token']
            vehicle.token_expires_at = expiration
            vehicle.updated_at = datetime.utcnow()
        else:
            print(f"Vehicle {vehicle_id} not found, creating new vehicle")
            
            # Create a default user if none exists
            user = User.query.first()
            if not user:
                print("No users found, creating default user")
                user = User(
                    smartcar_user_id='default_user',
                    email='default@example.com'
                )
                db.session.add(user)
                db.session.commit()
                print(f"Created default user with ID: {user.id}")
            else:
                print(f"Using existing user with ID: {user.id}")
            
            # Create new vehicle
            vehicle = Vehicle(
                smartcar_vehicle_id=vehicle_id,
                access_token=access_token_data['access_token'],
                refresh_token=access_token_data['refresh_token'],
                token_expires_at=expiration,
                user_id=user.id
            )
            db.session.add(vehicle)
            print(f"Created new vehicle {vehicle_id} with user_id {user.id}")
        
        print("Committing to database...")
        db.session.commit()
        print(f"Successfully stored access token for vehicle {vehicle_id}")
        return True
    except Exception as e:
        print(f"Error storing access token: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return False

def get_access_token(vehicle_id):
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if vehicle:
            from datetime import datetime, timezone
            # Check if token_expires_at is not None before comparison
            # Make sure both datetimes are timezone-aware for comparison
            current_time = datetime.now(timezone.utc)
            if vehicle.token_expires_at:
                # If token_expires_at is timezone-naive, assume it's UTC
                if vehicle.token_expires_at.tzinfo is None:
                    token_expires_utc = vehicle.token_expires_at.replace(tzinfo=timezone.utc)
                else:
                    token_expires_utc = vehicle.token_expires_at
                
                if token_expires_utc > current_time:
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
    try:
        new_token = client.refresh_token(refresh_token)
        if new_token:
            store_access_token(vehicle_id, new_token)
        return new_token
    except Exception as e:
        print(f"Error refreshing token in database: {str(e)}")
        return None

# get user_id from vehicle
def get_user_id_from_vehicle(vehicle_id):
    vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
    if vehicle:
        user = User.query.get(vehicle.user_id)
        return user.smartcar_user_id if user else None
    return None


# store webhook data
def store_webhook_data(vehicle_id, event_type, data, raw_data=None, timestamp=None):
    try:
        if timestamp is None:
            timestamp = datetime.now()
        
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if not vehicle:
            print(f"Vehicle {vehicle_id} not found in database, creating placeholder vehicle")

            store_access_token(vehicle_id, {
                'access_token': 'placeholder', 
                'refresh_token': 'placeholder', 
                'expiration': datetime.now().timestamp()
            })
            
            vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
            if not vehicle:
                print(f"Could not find vehicle {vehicle_id} after attempting to create placeholder")
                return False
            print(f"Created placeholder vehicle {vehicle_id}")
        
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



@app.route('/')
def index():
    content = """
    <h2>Smartcar Server</h2>
    <div class="form-section">
        <h3>Connect Vehicle</h3>
        <a href="/login" class="btn">Connect Vehicle</a>
    </div>
    
    <div class="form-section">
        <h3>View Vehicle Info</h3>
        <form action="/vehicle" method="get">
            <label for="vehicle_id">Vehicle ID:</label>
            <input type="text" id="vehicle_id" name="vehicle_id" placeholder="Enter vehicle ID" required>
            <button type="submit" class="btn">View Vehicle</button>
        </form>
    </div>
    
    <div class="info-section">
        <h3>Quick Links</h3>
        <p><strong>Example Vehicle IDs:</strong></p>
        <ul>
            <li><code>31581c01-3f29-4906-a194-9c150d456ea8</code> - Tesla Model 3</li>
            <li><code>6ccdc0d5-dee8-4d61-b23d-59122081da7a</code> - Your connected vehicle</li>
        </ul>
    </div>
    """
    return render_template('base.html', content=content)

@app.route('/login')
def login():
    # Generate auth URL without requiring user_id
    auth_url = client.get_auth_url()
    return redirect(auth_url)


@app.route('/exchange')
def exchange():
    code = request.args.get('code')
    
    if not code:
        content = '<div class="error">authorization code not found in request</div>'
        return render_template('base.html', content=content)
    
    try:
        access_token = client.exchange_code(code)
        
        print(f"Received access token: {access_token}")
        
        # Store in database only - no session storage
        print(f"Storing token in database")
        
        try:
            vehicle_ids = smartcar.get_vehicle_ids(access_token['access_token'])
            if vehicle_ids['vehicles']:
                vehicle_id = vehicle_ids['vehicles'][0]
                
                vehicle = smartcar.Vehicle(vehicle_id, access_token['access_token'])
                vehicle_info = vehicle.info()
                
                store_access_token(vehicle_id, access_token)
                
                db_vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
                if db_vehicle:
                    db_vehicle.make = vehicle_info.get('make')
                    db_vehicle.model = vehicle_info.get('model')
                    db_vehicle.year = vehicle_info.get('year')
                    db.session.commit()
                    print(f"Updated vehicle info for {vehicle_id}")
                else:
                    print(f"Warning: Vehicle {vehicle_id} not found in database after storing token")
            else:
                print(f"Warning: No vehicles found")
                vehicle_id = None
        except Exception as e:
            print(f"Error storing vehicle info in database: {str(e)}")
            vehicle_id = None
        
        # No user_id to persist

        return jsonify({
            'status': 'success',
            'message': 'Vehicle connected successfully',
            'vehicle_id': vehicle_id if 'vehicle_id' in locals() else None,
            'access_token': access_token['access_token'] if 'access_token' in locals() else None
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error exchanging code: {str(e)}'
        }), 400

@app.route('/vehicle')
def vehicle():
    try:
        # Get vehicle_id from query parameter
        vehicle_id = request.args.get('vehicle_id')
        
        if not vehicle_id:
            content = '''
            <div class="error">
                <h3>Vehicle ID Required</h3>
                <p>Please provide a vehicle_id parameter to view vehicle data.</p>
                <p>Example: <code>/vehicle?vehicle_id=your_vehicle_id</code></p>
                <a href="/" class="btn">Back to Home</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        # Find vehicle directly by vehicle_id
        print(f"Looking for vehicle with ID: {vehicle_id}")
        db_vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if not db_vehicle:
            print(f"Vehicle {vehicle_id} not found in database")
            content = f'''
            <div class="error">
                <h3>Vehicle Not Found</h3>
                <p>Vehicle ID "{vehicle_id}" not found in database.</p>
                <a href="/" class="btn">Back to Home</a>
            </div>
            '''
            return render_template('base.html', content=content)
        
        print(f"Found vehicle in database: {db_vehicle.smartcar_vehicle_id}")
        
        print(f"Found vehicle: {vehicle_id} ({db_vehicle.make} {db_vehicle.model} {db_vehicle.year})")
        
        token_data = get_access_token(vehicle_id)
        access_token = None
        if token_data:
            access_token = token_data['access_token']
            print(f"Using database token for vehicle {vehicle_id}")
        else:
            print(f"No valid access token found for vehicle {vehicle_id}")
        
        if not access_token:
            print(f"No access token available for vehicle {vehicle_id}")
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
        # Get latest location from database
        latest_location_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Location.PreciseLocation'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_location_entry:
            location_data = latest_location_entry.to_dict()['data']
            # Handle both old and new data structures
            if 'value' in location_data:
                # New enhanced structure
                location_value = location_data['value']
                lat = location_value.get('latitude', 'N/A')
                lng = location_value.get('longitude', 'N/A')
                direction = location_value.get('direction', 'N/A')
                heading = location_value.get('heading', 'N/A')
                location_type = location_value.get('locationType', 'N/A')
                location_info = f"<p><strong>Location:</strong> {lat}, {lng} (Direction: {direction}, Heading: {heading}, Type: {location_type}) (from webhook)</p>"
            else:
                # Old structure
                lat = location_data.get('latitude', 'N/A')
                lng = location_data.get('longitude', 'N/A')
                location_info = f"<p><strong>Location:</strong> {lat}, {lng} (from webhook)</p>"
        else:
            try:
                print("Getting vehicle location...")
                location = vehicle.location()
                print(f"Location response: {location}")
                location_info = f"<p><strong>Location:</strong> {location.get('data', {}).get('latitude', 'N/A')}, {location.get('data', {}).get('longitude', 'N/A')} (from API)</p>"
            except Exception as e:
                print(f"Error getting location: {str(e)}")
                location_info = "<p><strong>Location:</strong> Error retrieving location</p>"
        
        # --- Odometer ---
        # Get latest odometer from database
        latest_odometer_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Odometer.TraveledDistance'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_odometer_entry:
            odometer_data = latest_odometer_entry.to_dict()['data']
            # Handle both old and new data structures
            if 'value' in odometer_data:
                # New enhanced structure
                odometer_value = odometer_data['value']
                distance = odometer_value.get('value', 'N/A')
                odometer_info = f"<p><strong>Odometer:</strong> {distance} km (from webhook)</p>"
            else:
                # Old structure
                distance = odometer_data.get('distance', odometer_data.get('value', 'N/A'))
                odometer_info = f"<p><strong>Odometer:</strong> {distance} km (from webhook)</p>"
        else:
            try:
                print("Getting vehicle odometer...")
                odometer = vehicle.odometer()
                print(f"Odometer response: {odometer}")
                odometer_info = f"<p><strong>Odometer:</strong> {odometer.get('data', {}).get('distance', odometer.get('data', {}).get('value', 'N/A'))} km (from API)</p>"
            except Exception as e:
                print(f"Error getting odometer: {str(e)}")
                odometer_info = "<p><strong>Odometer:</strong> Error retrieving odometer</p>"
        

        latest_battery_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='TractionBattery.StateOfCharge'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_battery_entry:
            soc_data = latest_battery_entry.to_dict()['data']
            # Handle both old and new data structures
            if 'value' in soc_data:
                # New enhanced structure
                soc_value_data = soc_data['value']
                soc_value = soc_value_data.get('value', 'N/A')
                soc_info = f"<p><strong>State of Charge:</strong> {soc_value}% (from webhook)</p>"
            else:
                # Old structure
                soc_value = soc_data.get('percentage', soc_data.get('value', 'N/A'))
                soc_info = f"<p><strong>State of Charge:</strong> {soc_value}% (from webhook)</p>"
        else:
            soc_info = "<p><strong>State of Charge:</strong> N/A</p>"
        

        latest_capacity_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='TractionBattery.NominalCapacity'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_capacity_entry:
            capacity_data = latest_capacity_entry.to_dict()['data']
            # Handle both old and new data structures
            if 'value' in capacity_data:
                # New enhanced structure
                capacity_value_data = capacity_data['value']
                capacity_value = capacity_value_data.get('capacity', 'N/A')
                capacity_info = f"<p><strong>Nominal Capacity:</strong> {capacity_value} kWh (from webhook)</p>"
            else:
                # Old structure
                capacity_value = capacity_data.get('capacity', 'N/A')
                capacity_info = f"<p><strong>Nominal Capacity:</strong> {capacity_value} kWh (from webhook)</p>"
        else:
            capacity_info = "<p><strong>Nominal Capacity:</strong> N/A</p>"

        latest_charge_limits_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Charge.ChargeLimits'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_charge_limits_entry:
            charge_limits_data = latest_charge_limits_entry.to_dict()['data']
            # Handle both old and new data structures
            if 'value' in charge_limits_data:
                # New enhanced structure
                charge_limits_value_data = charge_limits_data['value']
                active_limit = charge_limits_value_data.get('values', {}).get('activeLimit', 'N/A')
                charge_limits_info = f"<p><strong>Charge Limits:</strong> Active Limit: {active_limit}% (from webhook)</p>"
            else:
                # Old structure
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
        
    except Exception as e:
        print(f"Error in vehicle route: {str(e)}")
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

        # Check for verification request first
        if data.get('eventName') == 'verify':
            return handle_verification(data)

        # Handle VEHICLE_STATE format with signals array
        if data.get("eventType") == "VEHICLE_STATE" and "data" in data and "signals" in data["data"]:
            # Extract event metadata
            event_id = data.get("eventId")
            webhook_id = data.get("meta", {}).get("webhookId")
            delivery_id = data.get("meta", {}).get("deliveryId")
            delivered_at = data.get("meta", {}).get("deliveredAt")
            mode = data.get("meta", {}).get("mode")
            signal_count = data.get("meta", {}).get("signalCount")
            
            # Extract user and vehicle info
            user_info = data["data"].get("user", {})
            user_id_from_webhook = user_info.get("id")
            vehicle_info = data["data"]["vehicle"]
            vehicle_id = vehicle_info["id"]
            signals = data["data"]["signals"]
            
            print(f"Processing VEHICLE_STATE payload:")
            print(f"  Event ID: {event_id}")
            print(f"  Webhook ID: {webhook_id}")
            print(f"  User ID: {user_id_from_webhook}")
            print(f"  Vehicle ID: {vehicle_id}")
            print(f"  Signal Count: {signal_count}")
            print(f"  Mode: {mode}")
            
            # Update vehicle info if it exists, or create placeholder
            vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
            user_id = None
            if vehicle:
                # Update existing vehicle with info from webhook
                vehicle.make = vehicle_info.get("make")
                vehicle.model = vehicle_info.get("model")
                vehicle.year = vehicle_info.get("year")
                vehicle.updated_at = datetime.utcnow()
                db.session.commit()
                print(f"Updated vehicle info for {vehicle_id}")
                
                # Get user_id from the vehicle using helper function
                user_id = get_user_id_from_vehicle(vehicle_id)
                print(f"Found existing vehicle with user_id: {user_id}")
            else:
                # Use user_id from webhook if available, otherwise default
                user_id = user_id_from_webhook if user_id_from_webhook else 'default_user'
                print(f"Creating new vehicle with user_id: {user_id}")
            
            for signal in signals:
                signal_code = signal.get("code", "")
                signal_name = signal.get("name", "")
                signal_group = signal.get("group", "")
                signal_body = signal.get("body", {})
                signal_meta = signal.get("meta", {})
                
                # Extract timing information from signal metadata
                oem_updated_at = signal_meta.get("oemUpdatedAt")
                retrieved_at = signal_meta.get("retrievedAt")
                
                # Create enhanced data structure with metadata
                enhanced_data = {
                    "value": signal_body,
                    "metadata": {
                        "signal_name": signal_name,
                        "signal_group": signal_group,
                        "oem_updated_at": oem_updated_at,
                        "retrieved_at": retrieved_at,
                        "event_id": event_id,
                        "webhook_id": webhook_id,
                        "delivery_id": delivery_id,
                        "delivered_at": delivered_at,
                        "mode": mode
                    }
                }
                
                # Map signal codes to event types
                if signal_code == "location-preciselocation":
                    store_webhook_data(vehicle_id, "Location.PreciseLocation", enhanced_data, raw_data=data)
                    print(f"Stored Location.PreciseLocation for vehicle {vehicle_id} (lat: {signal_body.get('latitude')}, lng: {signal_body.get('longitude')})")
                    
                elif signal_code == "odometer-traveleddistance":
                    store_webhook_data(vehicle_id, "Odometer.TraveledDistance", enhanced_data, raw_data=data)
                    print(f"Stored Odometer.TraveledDistance for vehicle {vehicle_id} (value: {signal_body.get('value')})")
                    
                elif signal_code == "tractionbattery-stateofcharge":
                    store_webhook_data(vehicle_id, "TractionBattery.StateOfCharge", enhanced_data, raw_data=data)
                    print(f"Stored TractionBattery.StateOfCharge for vehicle {vehicle_id} (value: {signal_body.get('value')}%)")
                    
                elif signal_code == "tractionbattery-nominalcapacity":
                    store_webhook_data(vehicle_id, "TractionBattery.NominalCapacity", enhanced_data, raw_data=data)
                    print(f"Stored TractionBattery.NominalCapacity for vehicle {vehicle_id} (capacity: {signal_body.get('capacity')} kWh)")
                    
                elif signal_code == "charge-chargelimits":
                    store_webhook_data(vehicle_id, "Charge.ChargeLimits", enhanced_data, raw_data=data)
                    active_limit = signal_body.get('values', {}).get('activeLimit')
                    print(f"Stored Charge.ChargeLimits for vehicle {vehicle_id} (active limit: {active_limit}%)")
                else:
                    print(f"Unknown signal code: {signal_code} for vehicle {vehicle_id}")
            
            return {'status': 'success', 'message': 'VEHICLE_STATE payload processed'}, 200
        
        # If we reach here, the payload format is not supported
        print(f"Unsupported webhook payload format: {data}")
        return {'status': 'error', 'message': 'Unsupported webhook payload format'}, 400
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500

def handle_verification(data):
    try:
        challenge = data.get('payload', {}).get('challenge')
        webhook_id = data.get('webhookId')
        
        management_token = os.getenv('SMARTCAR_MANAGEMENT_TOKEN')
        
        if not management_token:
            return {'error': 'management token not configured'}, 500
        
        if not challenge:
            return {'error': 'no challenge provided'}, 400
        
        hmac_hash = hmac.new(
            management_token.encode('utf-8'),
            challenge.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"Generated HMAC: {hmac_hash}")
        
        return {'challenge': hmac_hash}, 200
        
    except Exception as e:
        return {'error': str(e)}, 500


# api endpoints
@app.route('/api/vehicle/<vehicle_id>/access-token')
def get_vehicle_access_token(vehicle_id):
    """Get access token for a specific vehicle"""
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        return jsonify({
            'vehicle_id': vehicle_id,
            'access_token': vehicle.access_token,
            'token_expires_at': vehicle.token_expires_at.isoformat() if vehicle.token_expires_at else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vehicle/<vehicle_id>/latest-signals')
def get_vehicle_latest_signals(vehicle_id):
    """Get latest signals for a specific vehicle"""
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found'}), 404
        
        event_types = [
            'Location.PreciseLocation',
            'Odometer.TraveledDistance',
            'TractionBattery.StateOfCharge',
            'TractionBattery.NominalCapacity',
            'Charge.ChargeLimits'
        ]

        latest_signals = {}

        for event_type in event_types:
            latest_entry = WebhookData.query.filter_by(
                vehicle_id=vehicle.id,
                event_type=event_type
            ).order_by(WebhookData.timestamp.desc()).first()
            
            if latest_entry:
                latest_signals[event_type] = {
                    'timestamp': latest_entry.timestamp,
                    'data': latest_entry.to_dict()['data']
                }
            else:
                latest_signals[event_type] = None

        return jsonify({
            'vehicle_id': vehicle_id,
            'signals': latest_signals
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/migrate-db', methods=['POST'])
def migrate_database():
    """Migrate database schema (add app_user_id column if missing)"""
    try:
        from sqlalchemy import text
        
        # Ensure app_user_id column exists on users
        result = db.session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'app_user_id'
        """))
        exists = result.scalar() is not None
        
        if not exists:
            print("Adding app_user_id column to users table...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN app_user_id VARCHAR(255)"))
            # Optional unique index for app_user_id
            try:
                db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_app_user_id ON users(app_user_id)"))
            except Exception:
                pass
            db.session.commit()
            print("app_user_id column added.")
            
            # Backfill app_user_id if missing by copying existing smartcar_user_id
            users = User.query.all()
            updated = 0
            for u in users:
                if not getattr(u, 'app_user_id', None) and getattr(u, 'smartcar_user_id', None):
                    u.app_user_id = u.smartcar_user_id
                    updated += 1
            if updated:
                db.session.commit()
                print(f"Backfilled app_user_id for {updated} existing users")
            
            return {'status': 'success', 'message': f'app_user_id column added and {updated} users backfilled'}, 200
        else:
            return {'status': 'success', 'message': 'app_user_id column already exists'}, 200
            
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/clear-all-data', methods=['POST'])
def clear_all_data():
    """Clear all data from database (users, vehicles, webhooks, sessions)"""
    try:
        # clear all webhook data
        webhook_count = WebhookData.query.count()
        WebhookData.query.delete()
        
        # clear all vehicles
        vehicle_count = Vehicle.query.count()
        Vehicle.query.delete()
        
        # clear all users
        user_count = User.query.count()
        User.query.delete()
        
        # clear all sessions
        session_count = UserSession.query.count()
        UserSession.query.delete()
        
        db.session.commit()
        
        return {
            'status': 'success', 
            'message': f'All data cleared: {user_count} users, {vehicle_count} vehicles, {webhook_count} webhooks, {session_count} sessions'
        }, 200
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500

@app.route('/debug/database')
def debug_database():
    """Debug endpoint to see what's in the database"""
    try:
        users = User.query.all()
        vehicles = Vehicle.query.all()
        webhooks = WebhookData.query.all()
        
        return jsonify({
            'users': [{'id': u.id, 'smartcar_user_id': u.smartcar_user_id, 'email': u.email} for u in users],
            'vehicles': [{'id': v.id, 'smartcar_vehicle_id': v.smartcar_vehicle_id, 'user_id': v.user_id, 'make': v.make, 'model': v.model} for v in vehicles],
            'webhooks': len(webhooks)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clear-webhook-data', methods=['POST'])
def clear_webhook_data():
    try:
        # clear all webhook data from database
        WebhookData.query.delete()
        db.session.commit()
        return {'status': 'success', 'message': 'All webhook data cleared from database'}, 200
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 500
