
"""
CyberSentinel - Live Monitoring Tests

Tests metadata aggregation without capturing
real network packets.
"""

import sys
from pathlib import Path


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from app.capture.flow_extractor import LiveFlowStore


def test_packet_aggregation():

    store = LiveFlowStore()

    store.record({
        "source": "192.168.1.2",
        "destination": "192.168.1.3",
        "source_port": 50200,
        "destination_port": 443,
        "protocol": "TCP",
        "size": 100
    })

    store.record({
        "source": "192.168.1.2",
        "destination": "192.168.1.3",
        "source_port": 50200,
        "destination_port": 443,
        "protocol": "TCP",
        "size": 200
    })

    result = store.snapshot()

    assert result["total_packets"] == 2
    assert result["total_bytes"] == 300

    assert result["active_flows"] == 1

    assert result["flows"][0]["packets"] == 2
    assert result["flows"][0]["bytes"] == 300

    assert result["protocols"][0]["name"] == "TCP"


def test_reset():

    store = LiveFlowStore()

    store.record({
        "source": "192.168.1.2",
        "destination": "192.168.1.1",
        "source_port": 5000,
        "destination_port": 53,
        "protocol": "UDP",
        "size": 77
    })

    store.reset()

    result = store.snapshot()

    assert result["total_packets"] == 0
    assert result["total_bytes"] == 0
    assert result["active_flows"] == 0
    assert result["flows"] == []


def test_protocol_distribution():

    store = LiveFlowStore()

    store.record({
        "source": "192.168.1.2",
        "destination": "192.168.1.1",
        "protocol": "TCP",
        "size": 100
    })

    store.record({
        "source": "192.168.1.2",
        "destination": "192.168.1.1",
        "protocol": "UDP",
        "size": 200
    })

    result = store.snapshot()

    protocols = {
        item["name"]: item["packets"]
        for item in result["protocols"]
    }

    assert protocols["TCP"] == 1
    assert protocols["UDP"] == 1
