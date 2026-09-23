from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'carbon.db'}"
MODEL_PATH = BASE_DIR / "ml" / "model.joblib"
METRICS_PATH = BASE_DIR / "ml" / "metrics.json"
