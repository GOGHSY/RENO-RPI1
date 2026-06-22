import logging

import requests

from ..utils import config

_log = logging.getLogger(__name__)


class VictoriaMetricsLogger:
    def __init__(self):
        self.url = f"{config.VM_URL}/write"

    def _send(self, line: str) -> None:
        for _ in range(3):
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
                _log.warning("VictoriaMetrics write failed, retrying: %s", e)

    def log(self, flow, v1_state, v2_state, turbidity, status) -> None:
        status_tag = status.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")
        fields = (
            f"flow_rate={float(flow)},"
            f"valve_1_active={1 if v1_state else 0},"
            f"valve_2_active={1 if v2_state else 0}"
        )
        if turbidity is not None:
            fields += f",turbidity={float(turbidity)}"
        self._send(f"filtration,status={status_tag} {fields}")

    def log_treatment(self, data: dict) -> None:
        tags   = []
        fields = []

        if "pump1_state" in data:
            tags.append(f"pump1_state={data['pump1_state']}")

        for key, value in data.items():
            if key in {"timestamp", "pump1_state"}:
                continue
            try:
                fields.append(f"{key}={float(value)}")
            except (ValueError, TypeError):
                fields.append(f'{key}="{value}"')

        line = "water_treatment"
        if tags:
            line += "," + ",".join(tags)
        line += " " + ",".join(fields)

        self._send(line)
        _log.info("Logged %d treatment fields", len(fields))
