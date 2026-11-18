"""Build deterministic synthetic demo traffic, or clean a user-supplied CSV.

Run from project root: python scripts/preprocess.py
Or: python scripts/preprocess.py --input datasets/raw/traffic.csv
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import RAW_DIR, PROCESSED_DIR  # noqa: E402
from app.preprocessing.cleaner import clean_traffic  # noqa: E402


def make_demo_dataset(normal_count: int = 450, anomaly_count: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=16)
    for i in range(normal_count + anomaly_count):
        abnormal = i >= normal_count
        protocol = str(rng.choice(["TCP", "UDP", "ICMP"], p=[0.78, 0.18, 0.04]))
        if abnormal:
            duration = float(rng.uniform(0.01, 3.0))
            packets = int(rng.integers(1200, 11000))
            bytes_count = int(packets * rng.integers(550, 1400))
            dst_port = int(rng.choice([22, 23, 445, 3389, 8080, 6553]))
            src_ip = f"10.1.9.{int(rng.integers(1, 50))}"
        else:
            duration = float(rng.uniform(0.5, 35.0))
            packets = int(rng.integers(2, 240))
            bytes_count = int(packets * rng.integers(60, 950))
            dst_port = int(rng.choice([53, 80, 443, 22, 123]))
            src_ip = f"10.0.0.{int(rng.integers(1, 240))}"
        rows.append({
            "timestamp": (start + timedelta(seconds=round(i * 90 + int(rng.integers(0, 30))))).isoformat(),
            "src_ip": src_ip, "dst_ip": f"10.0.2.{int(rng.integers(1, 200))}",
            "protocol": protocol, "src_port": int(rng.integers(1024, 65535)),
            "dst_port": dst_port, "duration": round(duration, 4),
            "packets": packets, "bytes": bytes_count, "label": int(abnormal),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="CSV with CyberSentinel traffic schema")
    args = parser.parse_args()
    if args.input:
        source = Path(args.input)
        if not source.is_absolute():
            source = ROOT / source
        df = pd.read_csv(source)
        print(f"Reading supplied dataset: {source}")
    else:
        df = make_demo_dataset()
        source = RAW_DIR / "demo_traffic.csv"
        df.to_csv(source, index=False)
        print(f"Created synthetic demo dataset: {source}")
    cleaned = clean_traffic(df)
    if len(cleaned) < 30:
        raise ValueError("At least 30 valid flows are required to train this example.")
    target = PROCESSED_DIR / "traffic_clean.csv"
    cleaned.to_csv(target, index=False)
    print(f"Saved {len(cleaned)} clean flows: {target}")


if __name__ == "__main__":
    main()
