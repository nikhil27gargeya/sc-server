# Smartcar Server

A Flask-based server for handling Smartcar webhooks and vehicle data with persistent PostgreSQL storage.

## Features

- **OAuth Authentication**: Connect vehicles via Smartcar OAuth
- **Webhook Processing**: Handle real-time vehicle data updates
- **Persistent Storage**: PostgreSQL database for storing tokens and webhook data
- **REST API**: Access vehicle data via REST endpoints
- **Token Management**: Automatic token refresh and storage

## Database Setup

### PostgreSQL Database (Recommended for Production)

The application is configured to use PostgreSQL for persistent storage of:
- User authentication tokens
- Vehicle information
- Webhook data
- User sessions

#### Database Configuration

1. **Set Environment Variables**:
   ```bash
   export DATABASE_URL="postgresql://username:password@host:port/database_name"
   ```

   For Render PostgreSQL:
   ```bash
   export DATABASE_URL="postgresql://smartcardb_user:3XxXGsB7BRs1LT1Q5gOuysyoknEQv4F6@dpg-d20jsjfgi27c73cn8270-a.oregon-postgres.render.com/smartcardb"
   ```

2. **Initialize Database**:
   ```bash
   python init_db.py
   ```

3. **Test Database Connection**:
   ```bash
   python test_db.py
   ```

### SQLite Database (Local Development)

For local development, the app will automatically use SQLite if no `DATABASE_URL` is set:
```bash
# No DATABASE_URL needed - will use sqlite:///webhook_data.db
python main.py
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export SMARTCAR_CLIENT_ID="your_client_id"
   export SMARTCAR_CLIENT_SECRET="your_client_secret"
   export SMARTCAR_REDIRECT_URI="http://localhost:8000/exchange"
   export SMARTCAR_MANAGEMENT_TOKEN="your_management_token"
   export SECRET_KEY="your_secret_key"
   export DATABASE_URL="your_database_url"  # Optional for local development
   ```

3. **Initialize Database**:
   ```bash
   python init_db.py
   ```

4. **Run the Application**:
   ```bash
   python main.py
   ```

## API Endpoints

### Web Interface
- `GET /` - Home page with navigation
- `GET /login` - Smartcar OAuth login
- `GET /vehicle` - Vehicle information dashboard
- `GET /webhook-data` - Webhook data dashboard

### REST API
- `GET /api/vehicles` - List all vehicles
- `GET /api/vehicle/{vehicle_id}/location` - Get vehicle location
- `GET /api/vehicle/{vehicle_id}/battery` - Get battery information
- `GET /api/vehicle/{vehicle_id}/odometer` - Get odometer reading
- `GET /api/vehicle/{vehicle_id}/charge-limits` - Get charge limits
- `GET /api/vehicle/{vehicle_id}/all` - Get all vehicle data
- `GET /api/vehicle/{vehicle_id}/latest-signals` - Get latest signals

### Webhook Endpoint
- `POST /webhook` - Receive webhook data from Smartcar

## Database Schema

### Users Table
- `id` - Primary key
- `smartcar_user_id` - Smartcar user identifier
- `email` - User email
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Vehicles Table
- `id` - Primary key
- `smartcar_vehicle_id` - Smartcar vehicle identifier
- `user_id` - Foreign key to users table
- `make` - Vehicle make
- `model` - Vehicle model
- `year` - Vehicle year
- `access_token` - OAuth access token
- `refresh_token` - OAuth refresh token
- `token_expires_at` - Token expiration timestamp
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Webhook Data Table
- `id` - Primary key
- `vehicle_id` - Foreign key to vehicles table
- `event_type` - Type of webhook event
- `timestamp` - Event timestamp
- `data` - Event data (JSON)
- `raw_data` - Full webhook payload (JSON)
- `created_at` - Creation timestamp

### User Sessions Table
- `id` - Primary key
- `user_id` - Foreign key to users table
- `session_token` - Session token
- `expires_at` - Session expiration timestamp
- `created_at` - Creation timestamp

## Webhook Events Supported

The application processes the following webhook events:
- `Location.PreciseLocation` - Vehicle GPS coordinates
- `Odometer.TraveledDistance` - Total distance traveled
- `TractionBattery.StateOfCharge` - Battery charge percentage
- `TractionBattery.NominalCapacity` - Battery capacity
- `Charge.ChargeLimits` - Battery charging limits

## Development

### Running Tests
```bash
python test_db.py  # Test database connection
```

### Database Management
```bash
python init_db.py  # Initialize database tables
```

### Clearing Data
```bash
curl -X POST http://localhost:8000/clear-webhook-data
```

## Deployment

### Render Deployment
1. Connect your repository to Render
2. Set environment variables in Render dashboard
3. Deploy with the following build command:
   ```bash
   pip install -r requirements.txt && python init_db.py
   ```

### Environment Variables for Production
- `DATABASE_URL` - PostgreSQL connection string
- `SMARTCAR_CLIENT_ID` - Smartcar application client ID
- `SMARTCAR_CLIENT_SECRET` - Smartcar application client secret
- `SMARTCAR_REDIRECT_URI` - OAuth redirect URI
- `SMARTCAR_MANAGEMENT_TOKEN` - Smartcar management token
- `SECRET_KEY` - Flask secret key

## Troubleshooting

### Database Connection Issues
1. Verify `DATABASE_URL` is correctly set
2. Check database credentials and permissions
3. Run `python test_db.py` to test connection
4. Ensure database tables are created with `python init_db.py`

### Token Issues
1. Check if tokens are being stored in database
2. Verify token refresh logic
3. Check Smartcar application settings

### Webhook Issues
1. Verify webhook URL is correctly configured in Smartcar
2. Check webhook verification process
3. Monitor webhook data storage in database
