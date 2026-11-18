
"""Scapy capture service; packet payloads are never retained."""

from datetime import datetime, timezone
from threading import Event, Lock, Thread
from time import time

from app.capture.flow_extractor import LiveFlowStore


class CaptureService:
    def __init__(self):
        self._lock = Lock()
        self._store = LiveFlowStore()

        self._stop = Event()
        self._worker = None

        self._interface = None
        self._started_at = None
        self._stopped_at = None
        self._error = None

    def interfaces(self):
        from scapy.all import conf, get_if_list

        names = list(dict.fromkeys(
            str(name) for name in get_if_list()
        ))

        default = str(conf.iface)

        return {
            "default": default,
            "interfaces": [
                {
                    "name": name,
                    "is_default": name == default
                }
                for name in names
            ]
        }

    def start(self, interface=None):
        available = self.interfaces()

        valid = [
            item["name"]
            for item in available["interfaces"]
        ]

        if interface is not None and interface not in valid:
            raise ValueError(
                "Choose an interface returned by "
                "/api/live/interfaces."
            )

        with self._lock:
            if (
                self._worker is not None
                and self._worker.is_alive()
            ):
                raise ValueError(
                    "Capture is already running or stopping."
                )

            self._stop = Event()
            self._store.reset()

            self._interface = (
                interface or available["default"]
            )

            self._started_at = time()
            self._stopped_at = None
            self._error = None

            self._worker = Thread(
                target=self._capture_loop,
                args=(interface, self._stop),
                daemon=True,
                name="CyberSentinelCapture"
            )

            self._worker.start()

        return self.status()

    def _on_packet(self, packet):
        from scapy.layers.inet import IP, TCP, UDP, ICMP
        from scapy.layers.inet6 import IPv6
        from scapy.layers.l2 import ARP

        try:
            if IP in packet:
                source = packet[IP].src
                destination = packet[IP].dst

            elif IPv6 in packet:
                source = packet[IPv6].src
                destination = packet[IPv6].dst

            elif ARP in packet:
                source = packet[ARP].psrc
                destination = packet[ARP].pdst

            else:
                return

            source_port = None
            destination_port = None

            if TCP in packet:
                protocol = "TCP"

                source_port = int(
                    packet[TCP].sport
                )

                destination_port = int(
                    packet[TCP].dport
                )

            elif UDP in packet:
                protocol = "UDP"

                source_port = int(
                    packet[UDP].sport
                )

                destination_port = int(
                    packet[UDP].dport
                )

            elif ICMP in packet:
                protocol = "ICMP"

            elif ARP in packet:
                protocol = "ARP"

            else:
                protocol = "IP/IPv6"

            # Save packet metadata, not its payload.
            self._store.record({
                "source": source,
                "destination": destination,
                "source_port": source_port,
                "destination_port": destination_port,
                "protocol": protocol,
                "size": len(packet)
            })

        except (
            ValueError,
            TypeError,
            AttributeError,
            IndexError
        ):
            return

    def _capture_loop(self, interface, stop):
        try:
            from scapy.all import sniff

            while not stop.is_set():
                sniff(
                    iface=interface,
                    prn=self._on_packet,
                    store=False,
                    timeout=1,
                    promisc=False
                )

        except Exception as exc:
            with self._lock:
                self._error = f"Capture failed: {exc}"

        finally:
            with self._lock:
                self._stopped_at = time()

            stop.set()

    def stop(self):
        with self._lock:
            worker = self._worker
            self._stop.set()

        if worker is not None and worker.is_alive():
            worker.join(timeout=3)

        with self._lock:
            if (
                self._started_at is not None
                and self._stopped_at is None
            ):
                self._stopped_at = time()

        return self.status()

    def model_flows(self):
        return self._store.model_flows()

    def status(self):
        with self._lock:
            alive = (
                self._worker is not None
                and self._worker.is_alive()
            )

            running = bool(
                alive and not self._stop.is_set()
            )

            stopping = bool(
                alive and self._stop.is_set()
            )

            started_at = self._started_at
            stopped_at = self._stopped_at
            interface = self._interface
            error = self._error

        elapsed = (
            max(
                0,
                int(
                    (stopped_at or time()) - started_at
                )
            )
            if started_at
            else 0
        )

        return {
            "running": running,
            "stopping": stopping,
            "interface": interface,

            "started_at": (
                datetime.fromtimestamp(
                    started_at,
                    timezone.utc
                ).isoformat()
                if started_at
                else None
            ),

            "elapsed_seconds": elapsed,
            "error": error,

            **self._store.snapshot(
                frozen=not running
            ),

            "notice": (
                "Metadata only; no payloads stored. "
                "Instantaneous rates describe the last "
                "five seconds; average rates cover the "
                "capture session. Live flow anomaly flags "
                "require a separately trained local baseline."
            )
        }


capture_service = CaptureService()
