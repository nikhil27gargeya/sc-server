from sqlalchemy import create_engine, Column, String, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import uuid

# Create SQLite database engine
engine = create_engine('sqlite:///webhook_data.db', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class WebhookEvent(Base):
    """Model for storing webhook events from Smartcar"""
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    raw_payload = Column(Text, nullable=False)  # JSON string of original webhook data
    processed_data = Column(Text)  # JSON string of cleaned/processed data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<WebhookEvent(vehicle_id='{self.vehicle_id}', event_type='{self.event_type}', timestamp='{self.timestamp}')>"
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "raw_payload": json.loads(self.raw_payload) if self.raw_payload else {},
            "processed_data": json.loads(self.processed_data) if self.processed_data else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_webhook_payload(cls, payload):
        """Create a WebhookEvent from a webhook payload"""
        event = cls(
            vehicle_id=payload.get('vehicleId'),
            event_type=payload.get('eventType'),
            timestamp=datetime.fromisoformat(payload.get('timestamp').replace('Z', '+00:00')) if payload.get('timestamp') else datetime.utcnow(),
            raw_payload=json.dumps(payload),
            processed_data=json.dumps(cls._process_webhook_data(payload))
        )
        return event
    
    @staticmethod
    def _process_webhook_data(payload):
        """Process and clean webhook data based on event type"""
        event_type = payload.get('eventType')
        data = payload.get('data', {})
        
        if event_type == "Location.PreciseLocation":
            return {
                "latitude": float(data.get("latitude", 0)),
                "longitude": float(data.get("longitude", 0)),
                "accuracy": float(data.get("accuracy", 0)) if data.get("accuracy") else None
            }
        elif event_type == "TractionBattery.StateOfCharge":
            return {
                "percentage": float(data.get("percentage", 0)),
                "unit": "percent"
            }
        elif event_type == "TractionBattery.NominalCapacity":
            return {
                "capacity_kwh": float(data.get("capacity_kwh", 0)),
                "unit": "kWh"
            }
        elif event_type == "Odometer.TraveledDistance":
            return {
                "distance": float(data.get("distance", 0)),
                "unit": "kilometers"
            }
        elif event_type == "Charge.ChargeLimits":
            return {
                "max_percentage": float(data.get("max", 0)),
                "min_percentage": float(data.get("min", 0)),
                "unit": "percent"
            }
        else:
            # For unknown event types, return the raw data
            return data

# Create indexes for better query performance
Index('idx_vehicle_event_time', WebhookEvent.vehicle_id, WebhookEvent.event_type, WebhookEvent.timestamp)
Index('idx_timestamp', WebhookEvent.timestamp)

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 