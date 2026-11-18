import pandas as pd

REQUIRED_COLUMNS = [
    "timestamp", "src_ip", "dst_ip", "protocol", "src_port",
    "dst_port", "duration", "packets", "bytes",
]
NUMERIC_COLUMNS = ["src_port", "dst_port", "duration", "packets", "bytes"]


def clean_traffic(df: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    cleaned = df.copy()
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce", utc=True)
    for col in NUMERIC_COLUMNS:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
    cleaned = cleaned.dropna(subset=REQUIRED_COLUMNS)
    cleaned = cleaned[
        (cleaned["duration"] >= 0)
        & (cleaned["packets"] >= 1)
        & (cleaned["bytes"] >= 0)
        & (cleaned["src_port"].between(0, 65535))
        & (cleaned["dst_port"].between(0, 65535))
    ].copy()
    cleaned["protocol"] = cleaned["protocol"].astype(str).str.upper().str.strip()
    cleaned["src_port"] = cleaned["src_port"].astype(int)
    cleaned["dst_port"] = cleaned["dst_port"].astype(int)
    cleaned["packets"] = cleaned["packets"].astype(int)
    cleaned["bytes"] = cleaned["bytes"].astype(int)
    if "label" in cleaned.columns:
        cleaned["label"] = pd.to_numeric(cleaned["label"], errors="coerce").fillna(0).astype(int)
    return cleaned.sort_values("timestamp").reset_index(drop=True)
