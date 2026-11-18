import numpy as np
import pandas as pd

MODEL_FEATURES = [
    "duration", "src_port", "dst_port", "packets", "bytes",
    "packets_per_second", "bytes_per_second", "avg_packet_size",
    "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Produce exactly the same numeric feature order at training and inference."""
    result = pd.DataFrame(index=df.index)
    for col in ("duration", "src_port", "dst_port", "packets", "bytes"):
        result[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)
    safe_duration = np.maximum(result["duration"].to_numpy(), 0.001)
    safe_packets = np.maximum(result["packets"].to_numpy(), 1)
    result["packets_per_second"] = result["packets"].to_numpy() / safe_duration
    result["bytes_per_second"] = result["bytes"].to_numpy() / safe_duration
    result["avg_packet_size"] = result["bytes"].to_numpy() / safe_packets
    protocol = df["protocol"].fillna("OTHER").astype(str).str.upper()
    for name in ("TCP", "UDP", "ICMP"):
        result[f"proto_{name.lower()}"] = (protocol == name).astype(float)
    result["proto_other"] = (~protocol.isin(["TCP", "UDP", "ICMP"])).astype(float)
    return result[MODEL_FEATURES].replace([np.inf, -np.inf], 0).fillna(0)
