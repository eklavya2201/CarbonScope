"""Emission factors and helpers shared by the dashboard.

The factors match the ones used to generate the training data in ml/train_model.py,
so the transport / electricity split lines up with what the model learned.
"""
from datetime import timedelta, timezone

FUEL_FACTOR = {"Petrol": 2.31, "Diesel": 2.68, "CNG": 2.0, "Electric": 0.05, "Hybrid": 1.2}
VEHICLE_MULT = {"Car": 1.0, "Bus": 1.4, "Motorcycle": 0.65, "Truck": 1.8, "Train": 0.45, "EV": 0.35}
IST = timezone(timedelta(hours=5, minutes=30))

# Emission level bands used across the app (kg CO2 per prediction).
LEVELS = [("Low", 0, 5), ("Moderate", 5, 15), ("High", 15, float("inf"))]


def split(p):
    """Estimate how much of a prediction comes from fuel vs electricity.

    Returns (transport_kg, electricity_kg), scaled so they add up to the model's prediction.
    """
    transport = p.fuel_liters * FUEL_FACTOR.get(p.fuel_type, 2.0) * VEHICLE_MULT.get(p.vehicle_type, 1.0)
    transport *= 1 / (0.65 + 0.35 * p.passengers)
    energy = p.electricity_kwh * p.grid_factor * (1 - p.renewable_share / 100)
    raw = transport + energy
    if raw <= 0:
        return p.predicted_co2_kg, 0.0
    return p.predicted_co2_kg * transport / raw, p.predicted_co2_kg * energy / raw


def level(kg):
    for name, lo, hi in LEVELS:
        if lo <= kg < hi:
            return name
    return "High"


def to_ist(dt):
    """SQLite drops the timezone, so stored times are naive UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


# Vehicle and fuel pairs that make sense together, used for sample data.
VALID_PAIRS = {
    "Car": ["Petrol", "Diesel", "CNG", "Hybrid"],
    "Bus": ["Diesel", "CNG", "Electric"],
    "Motorcycle": ["Petrol"],
    "Truck": ["Diesel", "CNG"],
    "Train": ["Diesel", "Electric"],
    "EV": ["Electric"],
}
