import os
import smartcar
from flask import Flask, request, redirect, session, render_template_string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Debug: Print environment variables
print("Environment variables:")
print(f"SMARTCAR_CLIENT_ID: {os.getenv('SMARTCAR_CLIENT_ID')}")
print(f"SMARTCAR_CLIENT_SECRET: {os.getenv('SMARTCAR_CLIENT_SECRET')}")
print(f"SMARTCAR_REDIRECT_URI: {os.getenv('SMARTCAR_REDIRECT_URI')}")

# Initialize Smartcar client
client = smartcar.AuthClient(
    client_id=os.getenv('SMARTCAR_CLIENT_ID'),
    client_secret=os.getenv('SMARTCAR_CLIENT_SECRET'),
    redirect_uri=os.getenv('SMARTCAR_REDIRECT_URI'),
    scope=['read_vehicle_info', 'read_odometer', 'read_location'],
    test_mode=True  # Set to False for production
)

# HTML template for the pages
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smartcar Python SDK Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .btn { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }
        .btn:hover { background-color: #0056b3; }
        .info { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .error { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .success { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Smartcar Python SDK Demo</h1>
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    content = """
    <h2>Welcome to Smartcar Python SDK Demo</h2>
    <p>This demo shows how to integrate Smartcar's Python SDK with Flask.</p>
    <a href="/login" class="btn">Connect Your Vehicle</a>
    <a href="/vehicle" class="btn">View Vehicle Info</a>
    """
    return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/login')
def login():
    # Generate the authorization URL
    auth_url = client.get_auth_url()
    return redirect(auth_url)

@app.route('/exchange')
def exchange():
    # Exchange authorization code for access token
    code = request.args.get('code')
    
    if not code:
        content = '<div class="error">Authorization code not found in request</div>'
        return render_template_string(HTML_TEMPLATE, content=content)
    
    try:
        # Exchange the authorization code for an access token
        access_token = client.exchange_code(code)
        
        # Debug: Print the access token
        print(f"Received access token: {access_token}")
        
        # Store the access token in session
        session['access_token'] = access_token
        print(f"Stored access token in session: {session.get('access_token')}")
        
        content = '''
        <div class="success">
            <h3>Authentication Successful!</h3>
            <p>Your vehicle has been connected successfully.</p>
            <a href="/vehicle" class="btn">View Vehicle Information</a>
        </div>
        '''
        return render_template_string(HTML_TEMPLATE, content=content)
        
    except Exception as e:
        content = f'<div class="error">Error exchanging code: {str(e)}</div>'
        return render_template_string(HTML_TEMPLATE, content=content)

@app.route('/vehicle')
def vehicle():
    access_token = session.get('access_token')
    
    # Debug: Print session info
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
        return render_template_string(HTML_TEMPLATE, content=content)
    
    try:
        # Get vehicle information
        vehicle_ids = smartcar.get_vehicle_ids(access_token)
        
        if not vehicle_ids['vehicles']:
            content = '<div class="error">No vehicles found for this user</div>'
            return render_template_string(HTML_TEMPLATE, content=content)
        
        # Get the first vehicle
        vehicle_id = vehicle_ids['vehicles'][0]
        vehicle = smartcar.Vehicle(vehicle_id, access_token)
        
        # Get vehicle information
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
        
        return render_template_string(HTML_TEMPLATE, content=content)
        
    except Exception as e:
        content = f'''
        <div class="error">
            <h3>Error Retrieving Vehicle Information</h3>
            <p>Error: {str(e)}</p>
            <a href="/login" class="btn">Reconnect Your Vehicle</a>
        </div>
        '''
        return render_template_string(HTML_TEMPLATE, content=content)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 