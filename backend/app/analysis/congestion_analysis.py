import numpy as np
from app.database.models import TrafficFlow


def analyze_bursts(flows: list[TrafficFlow]) -> dict:
    """High throughput is a burst INDICATOR, not evidence of congestion."""
    if not flows:
        return {"threshold_bytes_per_second": 0, "high_throughput_flows": [], "note": "No data."}
    rates = np.array([f.bytes / max(f.duration, 0.001) for f in flows], dtype=float)
    threshold = float(np.percentile(rates, 90))
    indices = np.argsort(rates)[::-1][:10]
    return {
        "threshold_bytes_per_second": round(threshold, 2),
        "high_throughput_flows": [
            {"id": flows[int(i)].id, "src_ip": flows[int(i)].src_ip,
             "dst_ip": flows[int(i)].dst_ip,
             "bytes_per_second": round(float(rates[int(i)]), 2),
             "is_anomaly": flows[int(i)].is_anomaly}
            for i in indices if rates[int(i)] >= threshold
        ],
        "note": "Top-decile flow rates indicate bursts only. Confirm congestion using interface capacity, delay, drops and utilization.",
    }
