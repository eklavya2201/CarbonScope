from flask import Blueprint, jsonify, render_template, request, Response
from sqlalchemy import func
import csv, io, json, random
from datetime import datetime, timedelta, timezone
from app import db
from app.models import Prediction
from app.emissions import IST, LEVELS, VALID_PAIRS, level, split, to_ist
from config import METRICS_PATH, MODEL_PATH
import joblib
import pandas as pd

api = Blueprint("api", __name__)

MODEL = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

VEHICLES = ["Car", "Bus", "Motorcycle", "Truck", "Train", "EV"]
FUELS = ["Petrol", "Diesel", "CNG", "Electric", "Hybrid"]
FEATURES = (["distance_km", "fuel_liters", "passengers", "electricity_kwh", "grid_factor", "renewable_share"]
            + [f"vehicle_type_{v}" for v in VEHICLES] + [f"fuel_type_{f}" for f in FUELS])

def error(message, status=400):
    return jsonify({"ok": False, "error": message}), status

def validate_payload(data):
    required = ["vehicle_type","fuel_type","distance_km","fuel_liters","passengers",
                "electricity_kwh","grid_factor","renewable_share"]
    missing = [x for x in required if x not in data]
    if missing:
        return None, f"Missing fields: {', '.join(missing)}"

    try:
        values = {
            "vehicle_type": str(data["vehicle_type"]),
            "fuel_type": str(data["fuel_type"]),
            "distance_km": float(data["distance_km"]),
            "fuel_liters": float(data["fuel_liters"]),
            "passengers": int(data["passengers"]),
            "electricity_kwh": float(data["electricity_kwh"]),
            "grid_factor": float(data["grid_factor"]),
            "renewable_share": float(data["renewable_share"]),
        }
    except (ValueError, TypeError):
        return None, "Numeric fields contain invalid values."

    if values["vehicle_type"] not in VEHICLES:
        return None, "Invalid vehicle type."
    if values["fuel_type"] not in FUELS:
        return None, "Invalid fuel type."
    if not (0 < values["distance_km"] <= 5000):
        return None, "Distance must be between 0 and 5000 km."
    if not (0 <= values["fuel_liters"] <= 1000):
        return None, "Fuel must be between 0 and 1000 liters."
    if not (1 <= values["passengers"] <= 100):
        return None, "Passengers must be between 1 and 100."
    if not (0 <= values["electricity_kwh"] <= 10000):
        return None, "Electricity must be between 0 and 10000 kWh."
    if not (0 <= values["grid_factor"] <= 2):
        return None, "Grid factor must be between 0 and 2 kg CO2/kWh."
    if not (0 <= values["renewable_share"] <= 100):
        return None, "Renewable share must be between 0 and 100%."
    return values, None

def predict_values(v):
    # Feature order must match training.
    x = pd.DataFrame([[
        v["distance_km"], v["fuel_liters"], v["passengers"],
        v["electricity_kwh"], v["grid_factor"], v["renewable_share"],
        *[1 if v["vehicle_type"] == t else 0 for t in VEHICLES],
        *[1 if v["fuel_type"] == f else 0 for f in FUELS]
    ]], columns=FEATURES)
    return max(0.0, float(MODEL.predict(x)[0]))

def row_json(p):
    return {
        "id": p.id,
        "created_at": to_ist(p.created_at).isoformat(),
        "vehicle_type": p.vehicle_type,
        "fuel_type": p.fuel_type,
        "distance_km": p.distance_km,
        "fuel_liters": p.fuel_liters,
        "passengers": p.passengers,
        "electricity_kwh": p.electricity_kwh,
        "predicted_co2_kg": p.predicted_co2_kg
    }

@api.get("/")
def index():
    return render_template("index.html")

@api.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "CarbonScope API"})

@api.get("/api/model-metrics")
def model_metrics():
    if not METRICS_PATH.exists():
        return error("Model metrics not found.", 404)
    return jsonify(json.loads(METRICS_PATH.read_text()))

@api.post("/api/predict")
def predict():
    data = request.get_json(silent=True) or {}
    values, err = validate_payload(data)
    if err:
        return error(err)
    if MODEL is None:
        return error("ML model is not available. Run python ml/train_model.py.", 500)

    result = predict_values(values)
    p = Prediction(predicted_co2_kg=result, **values)
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "prediction": row_json(p)}), 201

@api.get("/api/predictions")
def predictions():
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 500)
    except ValueError:
        return error("limit must be a whole number.")
    rows = Prediction.query.order_by(Prediction.created_at.desc()).limit(limit).all()
    return jsonify({"ok": True, "items": [row_json(x) for x in rows]})

@api.delete("/api/predictions/<int:prediction_id>")
def delete_prediction(prediction_id):
    p = db.session.get(Prediction, prediction_id)
    if not p:
        return error("Prediction not found.", 404)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})

def _pct_change(now, before):
    if not before:
        return None
    return round((now - before) / before * 100, 1)


@api.get("/api/dashboard")
def dashboard():
    """Everything the dashboard needs in one call. ?vehicle=Car filters every panel."""
    vehicle = request.args.get("vehicle") or None
    q = Prediction.query
    if vehicle:
        if vehicle not in VEHICLES:
            return error("Invalid vehicle type.")
        q = q.filter(Prediction.vehicle_type == vehicle)
    rows = q.order_by(Prediction.created_at.asc()).all()

    now = datetime.now(timezone.utc)
    stamps = [to_ist(p.created_at) for p in rows]
    kg = [p.predicted_co2_kg for p in rows]
    total = sum(kg)
    count = len(rows)

    # Last 30 days compared with the 30 days before that.
    cut1, cut2 = now - timedelta(days=30), now - timedelta(days=60)
    recent = [k for k, t in zip(kg, stamps) if t >= cut1]
    prior = [k for k, t in zip(kg, stamps) if cut2 <= t < cut1]
    avg_recent = sum(recent) / len(recent) if recent else 0
    avg_prior = sum(prior) / len(prior) if prior else 0

    # Weekly totals for the last 52 weeks (oldest first).
    week0 = (now.astimezone(IST) - timedelta(weeks=51)).date()
    week0 -= timedelta(days=week0.weekday())
    weekly = [0.0] * 52
    for k, t in zip(kg, stamps):
        i = (t.date() - week0).days // 7
        if 0 <= i < 52:
            weekly[i] += k
    weeks = [{"start": (week0 + timedelta(weeks=i)).isoformat(), "co2": round(v, 2)} for i, v in enumerate(weekly)]

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_day = [0.0] * 7
    for k, t in zip(kg, stamps):
        by_day[t.weekday()] += k

    by_vehicle = {}
    for p in rows:
        tr, el = split(p)
        v = by_vehicle.setdefault(p.vehicle_type, {"vehicle": p.vehicle_type, "transport": 0.0, "electricity": 0.0, "count": 0})
        v["transport"] += tr
        v["electricity"] += el
        v["count"] += 1
    vehicles = sorted(by_vehicle.values(), key=lambda v: -(v["transport"] + v["electricity"]))
    for v in vehicles:
        v["co2"] = round(v["transport"] + v["electricity"], 2)
        v["share"] = round(v["co2"] / total * 100, 1) if total else 0
        v["transport"] = round(v["transport"], 2)
        v["electricity"] = round(v["electricity"], 2)

    by_fuel = {}
    for p in rows:
        by_fuel[p.fuel_type] = by_fuel.get(p.fuel_type, 0) + p.predicted_co2_kg
    fuels = [{"fuel": f, "co2": round(v, 2), "share": round(v / total * 100, 1) if total else 0}
             for f, v in sorted(by_fuel.items(), key=lambda x: -x[1])]

    transport = sum(split(p)[0] for p in rows)
    electricity = total - transport
    passenger_km = sum(p.passengers * p.distance_km for p in rows)

    levels = {name: 0 for name, _, _ in LEVELS}
    for k in kg:
        levels[level(k)] += 1

    return jsonify({
        "ok": True,
        "vehicle": vehicle,
        "stats": {
            "count": count,
            "total_co2_kg": round(total, 2),
            "average_co2_kg": round(total / count, 2) if count else 0,
            "change_total": _pct_change(sum(recent), sum(prior)),
            "change_average": _pct_change(avg_recent, avg_prior),
            "change_count": _pct_change(len(recent), len(prior)),
            "transport_kg": round(transport, 2),
            "electricity_kg": round(electricity, 2),
            "per_passenger_km_g": round(total / passenger_km * 1000, 1) if passenger_km else 0,
        },
        "weeks": weeks,
        "by_day": [{"day": d, "co2": round(v, 2)} for d, v in zip(days, by_day)],
        "by_vehicle": vehicles,
        "by_fuel": fuels,
        "levels": [{"level": name, "count": levels[name], "share": round(levels[name] / count * 100, 1) if count else 0,
                    "range": f"{lo:g}–{hi:g} kg" if hi != float("inf") else f"over {lo:g} kg"} for name, lo, hi in LEVELS],
        # Kept for anything still reading the old shape.
        "trend": [{"date": t.strftime("%Y-%m-%d %H:%M"), "co2": round(k, 3)} for k, t in list(zip(kg, stamps))[-30:]],
    })


@api.post("/api/sample-data")
def sample_data():
    """Adds realistic sample trips spread over the last year, each run through the model."""
    if MODEL is None:
        return error("ML model is not available. Run python ml/train_model.py.", 500)
    n = min(max(int((request.get_json(silent=True) or {}).get("count", 150)), 1), 500)
    rng = random.Random()
    now = datetime.now(timezone.utc)
    weights = {"Car": 5, "Motorcycle": 4, "Bus": 3, "Train": 2, "EV": 2, "Truck": 1}
    added = []
    for _ in range(n):
        vehicle = rng.choices(list(weights), weights=list(weights.values()))[0]
        fuel = rng.choice(VALID_PAIRS[vehicle])
        distance = round(rng.uniform(3, 60) if vehicle in ("Motorcycle", "Car", "EV") else rng.uniform(10, 220), 1)
        per_litre = {"Car": 14, "Motorcycle": 40, "Bus": 4, "Truck": 5, "Train": 25}.get(vehicle, 14)
        litres = 0.0 if fuel == "Electric" else round(max(0.1, distance / per_litre * rng.uniform(.85, 1.15)), 2)
        kwh = round(distance * rng.uniform(.12, .2), 1) if fuel == "Electric" else round(rng.uniform(0, 6), 1)
        values = {
            "vehicle_type": vehicle, "fuel_type": fuel, "distance_km": distance, "fuel_liters": litres,
            "passengers": rng.randint(8, 45) if vehicle in ("Bus", "Train") else rng.randint(1, 4 if vehicle == "Car" else 2),
            "electricity_kwh": kwh, "grid_factor": round(rng.uniform(.68, .74), 2),  # India's grid, per CEA
            "renewable_share": rng.choice([0, 0, 10, 20, 30]),
        }
        # More recent weeks get more trips, and weekdays more than weekends.
        when = now - timedelta(days=rng.triangular(0, 365, 0), hours=rng.uniform(0, 24))
        if when.astimezone(IST).weekday() >= 5 and rng.random() < .35:
            when -= timedelta(days=2)
        added.append(Prediction(predicted_co2_kg=predict_values(values), created_at=when, **values))
    db.session.add_all(added)
    db.session.commit()
    return jsonify({"ok": True, "added": len(added)}), 201


@api.delete("/api/predictions")
def clear_predictions():
    deleted = Prediction.query.delete()
    db.session.commit()
    return jsonify({"ok": True, "deleted": deleted})

@api.get("/api/export")
def export_csv():
    rows = Prediction.query.order_by(Prediction.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","created_at","vehicle_type","fuel_type","distance_km","fuel_liters",
                     "passengers","electricity_kwh","grid_factor","renewable_share","predicted_co2_kg"])
    for p in rows:
        writer.writerow([p.id,p.created_at.isoformat(),p.vehicle_type,p.fuel_type,p.distance_km,
                         p.fuel_liters,p.passengers,p.electricity_kwh,p.grid_factor,
                         p.renewable_share,p.predicted_co2_kg])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=carbon_predictions.csv"})
