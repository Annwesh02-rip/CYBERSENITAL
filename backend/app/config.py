from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = PROJECT_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DB_PATH = DATASETS_DIR / "cybersentinel.db"
MODEL_PATH = MODELS_DIR / "cybersentinel.joblib"
REPORT_PATH = MODELS_DIR / "training_report.json"

for directory in (RAW_DIR, PROCESSED_DIR, MODELS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
