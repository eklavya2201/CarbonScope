from datetime import datetime, timezone
from . import db

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    vehicle_type = db.Column(db.String(40), nullable=False)
    fuel_type = db.Column(db.String(30), nullable=False)
    distance_km = db.Column(db.Float, nullable=False)
    fuel_liters = db.Column(db.Float, nullable=False)
    passengers = db.Column(db.Integer, nullable=False)
    electricity_kwh = db.Column(db.Float, nullable=False)
    grid_factor = db.Column(db.Float, nullable=False)
    renewable_share = db.Column(db.Float, nullable=False)
    predicted_co2_kg = db.Column(db.Float, nullable=False)
