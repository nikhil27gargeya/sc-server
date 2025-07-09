import os
import smartcar
from flask import Flask, request, redirect, session, render_template
from dotenv import load_dotenv

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
        
    except Exception as e:
        content = f'''
        <div class="error">
            <h3>Error Retrieving Vehicle Information</h3>
            <p>Error: {str(e)}</p>
            <a href="/login" class="btn">Reconnect Your Vehicle</a>
        </div>
        '''
        return render_template('base.html', content=content)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000) 