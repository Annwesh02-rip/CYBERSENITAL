from app.database.models import TrafficFlow


def recommendations(flows: list[TrafficFlow]) -> list[dict]:
    if not flows:
        return [{"priority": "Info", "title": "Load a dataset", "detail": "Run the preprocessing and training scripts to populate the dashboard."}]
    alerts = sum(f.is_anomaly for f in flows)
    anomaly_pct = 100 * alerts / len(flows)
    advice = []
    if alerts:
        advice.append({
            "priority": "High" if anomaly_pct >= 10 else "Medium",
            "title": "Review flagged network flows",
            "detail": f"{alerts} of {len(flows)} flows were flagged ({anomaly_pct:.1f}%). Investigate source addresses, destinations and ports before making security decisions.",
        })
    risky_ports = sum(f.dst_port in (21, 22, 23, 3389, 445) for f in flows)
    if risky_ports:
        advice.append({
            "priority": "Medium", "title": "Validate exposure of administrative services",
            "detail": f"{risky_ports} flows target selected administration/file-sharing ports. Check access controls and expected usage; port use alone does not establish malicious activity.",
        })
    advice.append({
        "priority": "Info", "title": "Measure link health before tuning throughput",
        "detail": "Correlate flow bursts with measured interface utilization, latency and packet loss. No changes are applied automatically.",
    })
    advice.append({
        "priority": "Info", "title": "Validate on a real labeled test set",
        "detail": "Synthetic-demo metrics are not representative of operational detection accuracy. Test using a separate held-out public network dataset.",
    })
    return advice
