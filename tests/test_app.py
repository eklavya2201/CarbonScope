import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db

def test_health():
    app=create_app()
    client=app.test_client()
    r=client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True

def test_predict_and_history():
    app=create_app()
    app.config["TESTING"]=True
    client=app.test_client()
    payload={
        "vehicle_type":"Car","fuel_type":"Petrol","distance_km":20,
        "fuel_liters":2.5,"passengers":2,"electricity_kwh":5,
        "grid_factor":0.7,"renewable_share":20
    }
    r=client.post("/api/predict",json=payload)
    assert r.status_code == 201
    assert r.get_json()["prediction"]["predicted_co2_kg"] >= 0
    r=client.get("/api/predictions")
    assert r.status_code == 200
