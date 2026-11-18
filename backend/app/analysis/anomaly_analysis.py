from collections import Counter
from app.database.models import TrafficFlow


def summarize_flows(flows: list[TrafficFlow]) -> dict:
    anomalies = [f for f in flows if f.is_anomaly]
    protocols = Counter(flow.protocol for flow in flows)
    top_sources = Counter(flow.src_ip for flow in anomalies)
    return {
        "total_flows": len(flows),
        "anomaly_count": len(anomalies),
        "anomaly_rate": round(100 * len(anomalies) / len(flows), 2) if flows else 0,
        "total_bytes": sum(f.bytes for f in flows),
        "protocol_distribution": [
            {"name": proto, "value": count}
            for proto, count in protocols.most_common()
        ],
        "top_anomalous_sources": [
            {"ip": ip, "count": count} for ip, count in top_sources.most_common(5)
        ],
        "latest_timestamp": max((f.timestamp for f in flows), default=None),
    }
