from datetime import datetime

import requests

from ..utils import config


def _tag(value) -> str:
    """Escape a line-protocol tag value (spaces, commas, = break the line)."""
    return str(value).replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


class VictoriaMetricsLogger:
    def __init__(self):
        self.url = f"{config.VM_URL}/influx/write?precision=ms"  # line protocol; /api/v1/import is JSON-only and silently drops these

    def _send(self, line: str):
        for _ in range(3):  # retry 3 times
            try:
                r = requests.post(self.url, data=line, timeout=2)
                r.raise_for_status()
                return
            except Exception as e:
                print(f"[VictoriaMetrics] retrying: {e}")

    # -------------------------
    # 1. FIXED STRUCTURE LOGGER
    # -------------------------
    def log(self, flow, v1_state, v2_state, turbidity, status):
        """Logs filtration system data"""

        line = (
            f"filtration,"
            f"status={_tag(status)} "
            f"flow_rate={float(flow)},"
            f"valve_1_active={int(bool(v1_state))},"
            f"valve_2_active={int(bool(v2_state))},"
            f"turbidity={float(turbidity)} "
        )

        self._send(line)

    # -------------------------
    # 2. DYNAMIC SENSOR LOGGER
    # -------------------------
    def log_treatment(self, data):
        """
        Logs all sensor data dynamically into VictoriaMetrics
        """

        measurement = "water_treatment"

        tags = []
        fields = []

        # handle tags separately
        if "pump1_state" in data:
            tags.append(f"pump1_state={_tag(data['pump1_state'])}")

        # build fields
        for key, value in data.items():
            if key in {"timestamp", "pump1_state"}:
                continue

            try:
                fields.append(f"{key}={float(value)}")
            except (ValueError, TypeError):
                fields.append(f'{key}="{value}"')

        # timestamp (optional)
        ts = ""
        if "timestamp" in data:
            try:
                dt = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S.%f")
                ts = int(dt.timestamp() * 1000)
            except Exception:
                pass

        # assemble line protocol
        line = measurement

        if tags:
            line += "," + ",".join(tags)

        line += " " + ",".join(fields)

        if ts:
            line += f" {ts}"

        self._send(line)

        print(f"✓ Logged {len(data)} fields to VictoriaMetrics")
