import os
import smartcar
from smartcar import exceptions
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
def store_access_token(vehicle_id, access_token_data, user_id):
    try:
        from datetime import datetime, timezone
        expiration = datetime.fromtimestamp(access_token_data['expiration'], tz=timezone.utc)
        
        # Check if vehicle exists
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        
        if vehicle:
            vehicle.access_token = access_token_data['access_token']
            vehicle.refresh_token = access_token_data['refresh_token']
            vehicle.token_expires_at = expiration
            vehicle.updated_at = datetime.utcnow()
        else:
            # create new user if it's the first vehicle for this user_id
            user = User.query.filter_by(smartcar_user_id=user_id).first()
            # for test vehicle
            if not user:
                user = User(
                    smartcar_user_id=user_id,
                    email=f'user_{user_id}@example.com' # Placeholder email
                )
                db.session.add(user)
                db.session.flush()
            
            # Create new vehicle
            vehicle = Vehicle(
                smartcar_vehicle_id=vehicle_id,
                access_token=access_token_data['access_token'],
                refresh_token=access_token_data['refresh_token'],
                token_expires_at=expiration,
                user_id=user.id
            )
            db.session.add(vehicle)
        
        db.session.commit()
        print(f"Stored access token for vehicle {vehicle_id} for user {user_id}")
        return True
    except Exception as e:
        print(f"Error storing access token: {str(e)}")
        db.session.rollback()
        return False

def get_access_token(vehicle_id, user_id=None):
    try:
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if vehicle:
            from datetime import datetime, timezone
            if vehicle.token_expires_at > datetime.now(timezone.utc):
                return {
                    'access_token': vehicle.access_token,
                    'refresh_token': vehicle.refresh_token,
                    'expiration': vehicle.token_expires_at.timestamp()
                }
            else:
                # if user_id is not provided, try to get it from the vehicle
                if user_id is None:
                    user = User.query.get(vehicle.user_id)
                    user_id = user.smartcar_user_id if user else None
                
                return refresh_access_token_db(vehicle.refresh_token, vehicle_id, user_id)
        return None
    except Exception as e:
        print(f"Error getting access token: {str(e)}")
        return None

def refresh_access_token_db(refresh_token, vehicle_id, user_id=None):
    try:
        new_token = client.refresh_token(refresh_token)
        if new_token:
            # if user_id is not provided, try to get it from the vehicle
            if user_id is None:
                vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
                if vehicle:
                    user = User.query.get(vehicle.user_id)
                    user_id = user.smartcar_user_id if user else 'default_user'
                else:
                    user_id = 'default_user'
            
            store_access_token(vehicle_id, new_token, user_id)
            return new_token
        return None
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
def store_webhook_data(vehicle_id, event_type, data, raw_data=None, timestamp=None, user_id=None):
    try:
        if timestamp is None:
            timestamp = datetime.now()
        
        vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
        if not vehicle:
            print(f"Vehicle {vehicle_id} not found in database, creating placeholder vehicle")

            # Create placeholder vehicle with provided user_id or default
            if user_id is None:
                user_id = 'default_user'
            
            store_access_token(vehicle_id, {
                'access_token': 'placeholder', 
                'refresh_token': 'placeholder', 
                'expiration': datetime.now().timestamp()
            }, user_id)
            
            vehicle = Vehicle.query.filter_by(smartcar_vehicle_id=vehicle_id).first()
            if not vehicle:
                print(f"Could not find vehicle {vehicle_id} after attempting to create placeholder")
                return False
            print(f"Created placeholder vehicle {vehicle_id} for user {user_id}")
        
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
    <a href="/login" class="btn">Smartcar Connect</a>
    <a href="/vehicle" class="btn">Vehicle Info</a>
    <a href="/webhook-data" class="btn">Webhook Info</a>
    """
    return render_template('base.html', content=content)

@app.route('/login')
def login():
    # Get user_id from iOS app (passed as query parameter)
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'user_id parameter is required'}), 400
    
    # Store user_id in session for the exchange step
    session['pending_user_id'] = user_id
    
    # Generate auth URL with state parameter to include user_id
    auth_url = client.get_auth_url(state=user_id)
    return redirect(auth_url)

# Database-only token management - no session fallback

@app.route('/exchange')
def exchange():
    code = request.args.get('code')
    state = request.args.get('state')  # This will contain the user_id
    
    if not code:
        content = '<div class="error">Authorization code not found in request</div>'
        return render_template('base.html', content=content)
    
    # Get user_id from state parameter (sent by iOS app)
    user_id = state
    if not user_id:
        content = '<div class="error">User ID not found in state parameter</div>'
        return render_template('base.html', content=content)
    
    try:
        access_token = client.exchange_code(code)
        
        print(f"Received access token for user {user_id}: {access_token}")
        
        # Store in database only - no session storage
        print(f"Storing token in database for user {user_id}")
        
        # Get vehicle info to store in database
        try:
            vehicle_ids = smartcar.get_vehicle_ids(access_token['access_token'])
            if vehicle_ids['vehicles']:
                vehicle_id = vehicle_ids['vehicles'][0]
                
                # Get vehicle details
                vehicle = smartcar.Vehicle(vehicle_id, access_token['access_token'])
                vehicle_info = vehicle.info()
                
                # Store token in database with proper user_id
                store_access_token(vehicle_id, access_token, user_id)
                
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
        
        # Return JSON response for iOS app
        return jsonify({
            'status': 'success',
            'message': 'Vehicle connected successfully',
            'user_id': user_id,
            'vehicle_id': vehicle_id if 'vehicle_id' in locals() else None
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error exchanging code: {str(e)}'
        }), 400

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
            # Get user_id from the vehicle's user
            user = User.query.get(db_vehicle.user_id)
            user_id = user.smartcar_user_id if user else None
            token_data = get_access_token(vehicle_id, user_id)
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
        # Get latest location from database
        latest_location_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Location.PreciseLocation'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_location_entry:
            location_data = latest_location_entry.to_dict()['data']
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
        # Get latest odometer from database
        latest_odometer_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Odometer.TraveledDistance'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_odometer_entry:
            odometer_data = latest_odometer_entry.to_dict()['data']
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
        # Get latest battery from database
        latest_battery_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='TractionBattery.StateOfCharge'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_battery_entry:
            soc_data = latest_battery_entry.to_dict()['data']
            soc_value = soc_data.get('percentage', soc_data.get('value', 'N/A'))
            soc_info = f"<p><strong>State of Charge:</strong> {soc_value}% (from webhook)</p>"
        else:
            soc_info = "<p><strong>State of Charge:</strong> N/A</p>"
        
        # --- TractionBattery.NominalCapacity ---
        # Get latest capacity from database
        latest_capacity_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='TractionBattery.NominalCapacity'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_capacity_entry:
            capacity_data = latest_capacity_entry.to_dict()['data']
            capacity_value = capacity_data.get('capacity', 'N/A')
            capacity_info = f"<p><strong>Nominal Capacity:</strong> {capacity_value} kWh (from webhook)</p>"
        else:
            capacity_info = "<p><strong>Nominal Capacity:</strong> N/A</p>"
        
        # --- Charge.ChargeLimits or Charge.ChargeLimitConfiguration ---
        # Get latest charge limits from database
        latest_charge_limits_entry = WebhookData.query.filter_by(
            vehicle_id=db_vehicle.id,
            event_type='Charge.ChargeLimits'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if latest_charge_limits_entry:
            charge_limits_data = latest_charge_limits_entry.to_dict()['data']
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

        # Check for batch payload (VehicleState type) - old format
        if data.get("type") == "VehicleState" and "data" in data and "vehicles" in data["data"]:
            for vehicle in data["data"]["vehicles"]:
                vehicle_id = vehicle.get("vehicleId")
                signals = vehicle.get("signals", {})
                
                # Try to get user_id from the vehicle using helper function
                user_id = get_user_id_from_vehicle(vehicle_id)

                # Location.PreciseLocation
                loc = signals.get("location", {}).get("preciseLocation")
                if loc:
                    store_webhook_data(vehicle_id, "Location.PreciseLocation", loc, raw_data=data, user_id=user_id)

                # Odometer.TraveledDistance
                odo = signals.get("odometer", {}).get("traveledDistance")
                if odo:
                    store_webhook_data(vehicle_id, "Odometer.TraveledDistance", odo, raw_data=data, user_id=user_id)

                # TractionBattery.StateOfCharge
                soc = signals.get("tractionBattery", {}).get("stateOfCharge")
                if soc:
                    store_webhook_data(vehicle_id, "TractionBattery.StateOfCharge", soc, raw_data=data, user_id=user_id)

                # TractionBattery.NominalCapacity
                cap = signals.get("tractionBattery", {}).get("nominalCapacity")
                if cap:
                    store_webhook_data(vehicle_id, "TractionBattery.NominalCapacity", cap, raw_data=data, user_id=user_id)

                # Charge.ChargeLimits or Charge.ChargeLimitConfiguration
                charge_limits = signals.get("charge", {}).get("chargeLimits")
                if charge_limits:
                    store_webhook_data(vehicle_id, "Charge.ChargeLimits", charge_limits, raw_data=data, user_id=user_id)

            return {'status': 'success', 'message': 'Batch payload processed'}, 200

        # Check for new VEHICLE_STATE format with signals array
        elif data.get("eventType") == "VEHICLE_STATE" and "data" in data and "signals" in data["data"]:
            vehicle_id = data["data"]["vehicle"]["id"]
            vehicle_info = data["data"]["vehicle"]
            signals = data["data"]["signals"]
            
            print(f"Processing VEHICLE_STATE payload for vehicle {vehicle_id}")
            
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
            
            for signal in signals:
                signal_code = signal.get("code", "")
                signal_body = signal.get("body", {})
                
                # Map signal codes to event types
                if signal_code == "location-preciselocation":
                    store_webhook_data(vehicle_id, "Location.PreciseLocation", signal_body, raw_data=data, user_id=user_id)
                    print(f"Stored Location.PreciseLocation for vehicle {vehicle_id}")
                    
                elif signal_code == "odometer-traveleddistance":
                    store_webhook_data(vehicle_id, "Odometer.TraveledDistance", signal_body, raw_data=data, user_id=user_id)
                    print(f"Stored Odometer.TraveledDistance for vehicle {vehicle_id}")
                    
                elif signal_code == "tractionbattery-stateofcharge":
                    store_webhook_data(vehicle_id, "TractionBattery.StateOfCharge", signal_body, raw_data=data, user_id=user_id)
                    print(f"Stored TractionBattery.StateOfCharge for vehicle {vehicle_id}")
                    
                elif signal_code == "tractionbattery-nominalcapacity":
                    store_webhook_data(vehicle_id, "TractionBattery.NominalCapacity", signal_body, raw_data=data, user_id=user_id)
                    print(f"Stored TractionBattery.NominalCapacity for vehicle {vehicle_id}")
                    
                elif signal_code == "charge-chargelimits":
                    store_webhook_data(vehicle_id, "Charge.ChargeLimits", signal_body, raw_data=data, user_id=user_id)
                    print(f"Stored Charge.ChargeLimits for vehicle {vehicle_id}")
            
            return {'status': 'success', 'message': 'VEHICLE_STATE payload processed'}, 200

        # Fallback: handle as individual event (existing logic)
        # Check if this is a verification request
        if data.get('eventName') == 'verify':
            return handle_verification(data)
        
        # Store the webhook data with timestamp
        vehicle_id = data.get('vehicleId')
        event_type = data.get('eventType')
        event_data = data.get('data', {})
        
        # Try to get user_id from the vehicle using helper function
        user_id = get_user_id_from_vehicle(vehicle_id)
        
        # Store in database
        store_webhook_data(vehicle_id, event_type, event_data, raw_data=data, user_id=user_id)
        
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

@app.route('/api/user/<user_id>/vehicles')
def get_user_vehicles(user_id):
    """Get all vehicles for a specific user"""
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicles = Vehicle.query.filter_by(user_id=user.id).all()
        vehicle_data = []
        
        for vehicle in vehicles:
            vehicle_info = vehicle.to_dict()

            latest_location_entry = WebhookData.query.filter_by(
                vehicle_id=vehicle.id,
                event_type='Location.PreciseLocation'
            ).order_by(WebhookData.timestamp.desc()).first()
            
            latest_battery_entry = WebhookData.query.filter_by(
                vehicle_id=vehicle.id,
                event_type='TractionBattery.StateOfCharge'
            ).order_by(WebhookData.timestamp.desc()).first()
            
            latest_odometer_entry = WebhookData.query.filter_by(
                vehicle_id=vehicle.id,
                event_type='Odometer.TraveledDistance'
            ).order_by(WebhookData.timestamp.desc()).first()
                
            vehicle_info['latest_data'] = {
                'location': latest_location_entry.to_dict()['data'] if latest_location_entry else None,
                'battery': latest_battery_entry.to_dict()['data'] if latest_battery_entry else None,
                'odometer': latest_odometer_entry.to_dict()['data'] if latest_odometer_entry else None
            }
            vehicle_data.append(vehicle_info)
        
        return jsonify({
            'user_id': user_id,
            'vehicles': vehicle_data,
            'total_vehicles': len(vehicle_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/latest-signals')
def get_user_vehicle_latest_signals(user_id, vehicle_id):
    """Get latest signals for a specific user's vehicle"""
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
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
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'signals': latest_signals
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/location')
def get_user_vehicle_location(user_id, vehicle_id):
    """Get location data for a specific user's vehicle"""
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
        latest_location_entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type='Location.PreciseLocation'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if not latest_location_entry:
            return jsonify({'error': 'No location data found for this vehicle'}), 404
        
        return jsonify({
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'timestamp': latest_location_entry.timestamp,
            'location': latest_location_entry.to_dict()['data']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/odometer')
def get_user_vehicle_odometer(user_id, vehicle_id):
    """Get odometer data for a specific user's vehicle"""
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
        latest_odometer_entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type='Odometer.TraveledDistance'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if not latest_odometer_entry:
            return jsonify({'error': 'No odometer data found for this vehicle'}), 404
        
        return jsonify({
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'timestamp': latest_odometer_entry.timestamp,
            'odometer': latest_odometer_entry.to_dict()['data']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/state-of-charge')
def get_user_vehicle_state_of_charge(user_id, vehicle_id):
    """Get battery state of charge for a specific user's vehicle"""
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
        latest_soc_entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type='TractionBattery.StateOfCharge'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if not latest_soc_entry:
            return jsonify({'error': 'No state of charge data found for this vehicle'}), 404
        
        soc_data = latest_soc_entry.to_dict()['data']
        soc_value = soc_data.get('value', soc_data.get('percentage'))
        
        return jsonify({
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'timestamp': latest_soc_entry.timestamp,
            'state_of_charge': soc_value
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/nominal-capacity')
def get_user_vehicle_nominal_capacity(user_id, vehicle_id):
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
        latest_capacity_entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type='TractionBattery.NominalCapacity'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if not latest_capacity_entry:
            return jsonify({'error': 'No nominal capacity data found for this vehicle'}), 404

        capacity_data = latest_capacity_entry.to_dict()['data']
        capacity_value = None
        
        if 'capacity' in capacity_data:
            capacity_value = capacity_data['capacity']
        elif 'availableCapacities' in capacity_data and capacity_data['availableCapacities']:
            capacity_value = capacity_data['availableCapacities'][0].get('capacity')
        
        if capacity_value is None:
            return jsonify({'error': 'Could not extract capacity value from data'}), 404
        
        return jsonify({
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'timestamp': latest_capacity_entry.timestamp,
            'nominal_capacity': capacity_value
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/vehicle/<vehicle_id>/charge-limits')
def get_user_vehicle_charge_limits(user_id, vehicle_id):
    try:
        user = User.query.filter_by(smartcar_user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        vehicle = Vehicle.query.filter_by(
            smartcar_vehicle_id=vehicle_id,
            user_id=user.id
        ).first()
        
        if not vehicle:
            return jsonify({'error': 'Vehicle not found for this user'}), 404
        
        latest_charge_limits_entry = WebhookData.query.filter_by(
            vehicle_id=vehicle.id,
            event_type='Charge.ChargeLimits'
        ).order_by(WebhookData.timestamp.desc()).first()
        
        if not latest_charge_limits_entry:
            return jsonify({'error': 'No charge limits data found for this vehicle'}), 404
        
        charge_data = latest_charge_limits_entry.to_dict()['data']
        charge_limit_value = None
        
        if 'values' in charge_data:
            values_data = charge_data['values']
            if 'activeLimit' in values_data:
                charge_limit_value = values_data['activeLimit']
            elif 'values' in values_data and values_data['values']:
                for limit_item in values_data['values']:
                    if limit_item.get('type') == 'global':
                        charge_limit_value = limit_item.get('limit')
                        break
                if charge_limit_value is None and values_data['values']:
                    charge_limit_value = values_data['values'][0].get('limit')
        
        if charge_limit_value is None:
            return jsonify({'error': 'Could not extract charge limit value from data'}), 404
        
        return jsonify({
            'user_id': user_id,
            'vehicle_id': vehicle_id,
            'timestamp': latest_charge_limits_entry.timestamp,
            'charge_limit': charge_limit_value
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
