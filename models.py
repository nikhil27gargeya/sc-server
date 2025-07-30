from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    smartcar_user_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to vehicles
    vehicles = db.relationship('Vehicle', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'smartcar_user_id': self.smartcar_user_id,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    smartcar_vehicle_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to webhook data
    webhook_data = db.relationship('WebhookData', backref='vehicle', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'smartcar_vehicle_id': self.smartcar_vehicle_id,
            'user_id': self.user_id,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'token_expires_at': self.token_expires_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WebhookData(db.Model):
    __tablename__ = 'webhook_data'
    
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    data = db.Column(db.Text, nullable=False)  # JSON string
    raw_data = db.Column(db.Text, nullable=True)  # Full webhook payload as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vehicle_id': self.vehicle_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'data': json.loads(self.data) if self.data else {},
            'raw_data': json.loads(self.raw_data) if self.raw_data else {},
            'created_at': self.created_at.isoformat()
        }
    
    @property
    def data_dict(self):
        """Return parsed data as dictionary"""
        return json.loads(self.data) if self.data else {}
    
    @property
    def raw_data_dict(self):
        """Return parsed raw_data as dictionary"""
        return json.loads(self.raw_data) if self.raw_data else {}

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        } 