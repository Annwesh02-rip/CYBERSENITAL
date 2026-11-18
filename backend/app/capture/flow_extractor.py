
"""Bounded, metadata-only live traffic aggregation for CyberSentinel."""

from collections import Counter, OrderedDict
from datetime import datetime
from threading import Lock
from time import time


class LiveFlowStore:
    def __init__(self):
        self._lock = Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self._packets = 0
            self._bytes = 0
            self._protocols = Counter()
            self._flows = OrderedDict()
            self._seconds = {}
            self._last_packet_second = None

    def record(self, data):
        now = time()
        size = max(0, int(data.get("size", 0)))
        protocol = str(data.get("protocol", "OTHER"))
        source = str(data.get("source", "?"))
        destination = str(data.get("destination", "?"))
        source_port = data.get("source_port")
        destination_port = data.get("destination_port")

        key = (
            source,
            destination,
            source_port,
            destination_port,
            protocol
        )

        with self._lock:
            self._packets += 1
            self._bytes += size
            self._protocols[protocol] += 1

            second = int(now)
            self._last_packet_second = second

            bucket = self._seconds.setdefault(
                second, [0, 0]
            )

            bucket[0] += 1
            bucket[1] += size

            # Keep at most ten minutes of timeline data.
            for old in list(self._seconds):
                if old < second - 599:
                    del self._seconds[old]

            flow = self._flows.get(key)

            if flow is None:
                flow = {
                    "source": source,
                    "destination": destination,
                    "source_port": source_port,
                    "destination_port": destination_port,
                    "protocol": protocol,
                    "packets": 0,
                    "bytes": 0,
                    "first_seen_epoch": now,
                    "last_seen_epoch": now,
                }

                self._flows[key] = flow

            flow["packets"] += 1
            flow["bytes"] += size
            flow["last_seen_epoch"] = now

            self._flows.move_to_end(key)

            # Prevent unlimited memory consumption.
            if len(self._flows) > 2000:
                self._flows.popitem(last=False)

    def model_flows(self):
        """Return flow metadata for ML, not packet payloads."""
        with self._lock:
            return [
                dict(flow)
                for flow in self._flows.values()
            ]

    def snapshot(self, frozen=False):
        now = int(time())

        with self._lock:
            # Retain the final activity window after stopping.
            anchor = (
                self._last_packet_second
                if frozen and self._last_packet_second is not None
                else now
            )

            timeline = []

            for second in range(anchor - 29, anchor + 1):
                packets, size = self._seconds.get(
                    second, [0, 0]
                )

                timeline.append({
                    "time": datetime.fromtimestamp(
                        second
                    ).strftime("%H:%M:%S"),
                    "packets": packets,
                    "kbps": round(size / 1024, 2),
                    "bytes": size,
                })

            recent = [
                self._seconds.get(second, [0, 0])
                for second in range(now - 4, now + 1)
            ]

            flows = [
                dict(flow)
                for flow in self._flows.values()
            ]

            top_flows = [
                dict(flow)
                for flow in sorted(
                    flows,
                    key=lambda item: item["bytes"],
                    reverse=True
                )[:30]
            ]

            for flow in top_flows:
                flow["last_seen"] = (
                    datetime.fromtimestamp(
                        flow.pop("last_seen_epoch")
                    ).strftime("%H:%M:%S")
                )

                flow.pop("first_seen_epoch", None)

            return {
                "total_packets": self._packets,
                "total_bytes": self._bytes,

                "packets_per_second": round(
                    sum(item[0] for item in recent) / 5,
                    2
                ),

                "bytes_per_second": round(
                    sum(item[1] for item in recent) / 5,
                    2
                ),

                "active_flows": sum(
                    flow["last_seen_epoch"] >= anchor - 30
                    for flow in flows
                ),

                "protocols": [
                    {
                        "name": protocol,
                        "packets": count
                    }
                    for protocol, count
                    in self._protocols.most_common(8)
                ],

                "timeline": timeline,
                "flows": top_flows
            }
