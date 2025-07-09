import os
import smartcar
from smartcar import exceptions
from flask import Flask, request, redirect, session, render_template
from dotenv import load_dotenv
import hmac
import hashlib

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
    access_token = session.get('access_token')
    
    print(f"Session access_token: {access_token}")
    print(f"Session keys: {list(session.keys())}")
    
    if not access_token:
        content = '''
        <div class="error">
            <h3>No Access Token Found</h3>
            <p>Please authenticate your vehicle first.</p>
            <a href="/login" class="btn">Connect Your Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)
    
    try:
        vehicle_ids = smartcar.get_vehicle_ids(access_token)
        
        if not vehicle_ids['vehicles']:
            content = '<div class="error">No vehicles found for this user</div>'
            return render_template('base.html', content=content)
        
        vehicle_id = vehicle_ids['vehicles'][0]
        vehicle = smartcar.Vehicle(vehicle_id, access_token)
        
        info = vehicle.info()
        location = vehicle.location()
        odometer = vehicle.odometer()
        
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
            <p><strong>Latitude:</strong> {location['data']['latitude']}</p>
            <p><strong>Longitude:</strong> {location['data']['longitude']}</p>
        </div>
        
        <div class="info">
            <h3>Odometer</h3>
            <p><strong>Distance:</strong> {odometer['data']['distance']} {odometer['data']['unit']}</p>
        </div>
        
        <a href="/" class="btn">Back to Home</a>
        '''
        
        return render_template('base.html', content=content)
        
    except smartcar.exceptions.RateLimitError as e:
        content = f'''
        <div class="error">
            <h3>Rate Limit Reached</h3>
            <p>You've made too many requests to the Smartcar API. Please wait a few minutes before trying again.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/vehicle" class="btn">Try Again</a>
            <a href="/" class="btn">Back to Home</a>
        </div>
        '''
        return render_template('base.html', content=content)
        
    except smartcar.exceptions.AuthenticationError as e:
        content = f'''
        <div class="error">
            <h3>Authentication Error</h3>
            <p>Your access token has expired or is invalid. Please reconnect your vehicle.</p>
            <p><strong>Error:</strong> {str(e)}</p>
            <a href="/login" class="btn">Reconnect Your Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)
        
    except Exception as e:
        content = f'''
        <div class="error">
            <h3>Error Retrieving Vehicle Information</h3>
            <p>Error: {str(e)}</p>
            <a href="/login" class="btn">Reconnect Your Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhooks from Smartcar"""
    try:
        data = request.get_json()
        
        print(f"Received webhook data: {data}")
        
        if data.get('eventName') == 'verify':
            return handle_verification(data)
        
        vehicle_id = data.get('vehicleId')
        event_type = data.get('eventType')
        timestamp = data.get('timestamp')
        
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
    content = '''
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
        <h3>Webhook Endpoint</h3>
        <p><strong>URL:</strong> https://sc-server-o0m5.onrender.com/webhook</p>
        <p><strong>Method:</strong> POST</p>
        <p><strong>Content-Type:</strong> application/json</p>
    </div>
    
    <div class="info">
        <h3>Smartcar Dashboard Configuration</h3>
        <p>Use these URLs in your Smartcar Dashboard:</p>
        <ul>
            <li><strong>Vehicle Data Callback URI:</strong> https://sc-server-o0m5.onrender.com/webhook</li>
            <li><strong>Vehicle Error Callback URI:</strong> https://sc-server-o0m5.onrender.com/webhook</li>
        </ul>
    </div>
    
    <a href="/" class="btn">Back to Home</a>
    '''
    
    return render_template('base.html', content=content)

def handle_verification(data):
    """Handle Smartcar's webhook verification challenge"""
    try:
        # Get the challenge from the payload
        challenge = data.get('payload', {}).get('challenge')
        webhook_id = data.get('webhookId')
        
        print(f"Verification request for webhook ID: {webhook_id}")
        print(f"Challenge: {challenge}")
        
        # Get the management token from environment variables
        management_token = os.getenv('SMARTCAR_MANAGEMENT_TOKEN')
        
        if not management_token:
            print("Error: SMARTCAR_MANAGEMENT_TOKEN not found in environment variables")
            return {'error': 'Management token not configured'}, 500
        
        # Generate HMAC using the management token and challenge
        hmac_hash = hmac.new(
            management_token.encode('utf-8'),
            challenge.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        print(f"Generated HMAC: {hmac_hash}")
        
        # Return the challenge response
        return {'challenge': hmac_hash}, 200
        
    except Exception as e:
        print(f"Error handling verification: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 