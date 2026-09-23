# CarbonScope — Carbon Emission Prediction Full-Stack Project

A complete college-friendly full-stack ML application that predicts CO₂ emissions from transportation and energy consumption.

## Stack
- Frontend: HTML5, CSS3, vanilla JavaScript, Chart.js
- Backend: Python Flask REST API
- Database: SQLite + SQLAlchemy
- ML: Scikit-learn Random Forest Regressor
- Model training: included training script
- Tests: Pytest API/database smoke tests

## Features
- Responsive dashboard UI
- CO₂ prediction form
- Transportation + energy inputs
- Prediction history stored in SQLite
- Dashboard statistics
- Recent prediction table
- Emission trend chart
- Vehicle-type comparison chart
- Delete individual history records
- CSV export
- Model metrics endpoint
- Input validation on backend
- Error handling
- Health check endpoint

## Project structure
```text
carbon_emission_fullstack/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/
│   └── carbon_dataset.csv
├── ml/
│   ├── train_model.py
│   ├── model.joblib
│   └── metrics.json
├── tests/
│   └── test_app.py
├── config.py
├── run.py
├── requirements.txt
└── README.md
```

## Quick start (Windows)
Needs Python 3.11 or newer. Double-click `run.bat`. The first run installs the packages, then the app opens at http://127.0.0.1:5000.

The database starts empty. Click the settings icon (top right) and choose **Add 150 sample trips** to fill the dashboard with a year of sample data, or make predictions on the Predictor tab.

## 1. Create environment
Windows:
```bat
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies
```bash
pip install -r requirements.txt
```

## 3. Run
```bash
python run.py
```

Open:
`http://127.0.0.1:5000`

The database is automatically created and the included ML model is loaded.

## 4. Retrain model
```bash
python ml/train_model.py
```

This regenerates the model and metrics from the included dataset.

## API
- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/predictions`
- `POST /api/predict`
- `DELETE /api/predictions/<id>`
- `GET /api/export`
- `GET /api/model-metrics`

## Example POST body
```json
{
  "vehicle_type": "Car",
  "fuel_type": "Petrol",
  "distance_km": 25,
  "fuel_liters": 3,
  "passengers": 2,
  "electricity_kwh": 8,
  "grid_factor": 0.7,
  "renewable_share": 20
}
```

## Notes
The included dataset is synthetic/educational. It is designed for demonstrating the end-to-end application and ML workflow, not for real-world environmental reporting.
