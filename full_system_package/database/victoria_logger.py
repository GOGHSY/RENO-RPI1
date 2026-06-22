from datetime import datetime

import requests

from ..utils import config


class VictoriaMetricsLogger:
    def __init__(self):
        self.url = f"{config.VM_URL}/write"

    def _send(self, line: str):
        for _ in range(3):  # retry 3 times
            try:
                r = requests.post(
                    self.url,
                    data=line.encode("utf-8"),
                    headers={"Content-Type": "text/plain"},
                    timeout=2,
                )
                r.raise_for_status()
                return
            except Exception as e:
                print(f"[VictoriaMetrics] retrying: {e}")

    # -------------------------
    # 1. FIXED STRUCTURE LOGGER
    # -------------------------
    def log(self, flow, v1_state, v2_state, turbidity, status):
        """Logs filtration system data"""
        # Escape tag values per InfluxDB line protocol spec
        status_tag = status.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
        line = (
            f"filtration,status={status_tag} "
            f"flow_rate={float(flow)},"
            f"valve_1_active={1 if v1_state else 0},"
            f"valve_2_active={1 if v2_state else 0},"
            f"turbidity={float(turbidity)}"
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
            tags.append(f"pump1_state={data['pump1_state']}")

        # build fields
        for key, value in data.items():
            if key in {"timestamp", "pump1_state"}:
                continue

            try:
                fields.append(f"{key}={float(value)}")
            except (ValueError, TypeError):
                fields.append(f'{key}="{value}"')

        # assemble line protocol (no explicit timestamp — let VictoriaMetrics
        # use current ingest time so instant queries always find recent data)
        line = measurement

        if tags:
            line += "," + ",".join(tags)

        line += " " + ",".join(fields)

        self._send(line)

        print(f"✓ Logged {len(data)} fields to VictoriaMetrics")
