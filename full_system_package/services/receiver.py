import json
import logging
import time

import zenoh

from ..database.victoria_logger import VictoriaMetricsLogger

_log = logging.getLogger(__name__)

# Zenoh key (same as MQTT topic)
ZENOH_KEY = "reno/water/treatment/010"

# zenohd runs locally on this Pi — connect via loopback so this doesn't
# depend on Tailscale being up (RPi2's connection still needs Tailscale).
ZENOH_ROUTER = "tcp/127.0.0.1:7447"

influx = VictoriaMetricsLogger()


def listener(sample):
    try:
        payload = bytes(sample.payload).decode("utf-8")
        data = json.loads(payload)

        _log.info("Sensor data received: %s", data)
        influx.log_treatment(data)

    except Exception:
        _log.exception("Failed to process sensor data")


def start_receiver():
    _log.info("Connecting to Zenoh...")
    conf = zenoh.Config()
    conf.insert_json5("connect/endpoints", f'["{ZENOH_ROUTER}"]')
    z = zenoh.open(conf)
    _log.info("Subscribed to %s", ZENOH_KEY)
    sub = z.declare_subscriber(ZENOH_KEY, listener)
    _log.info("Listening for water treatment data...")
    try:
        while True:
            time.sleep(1)
    finally:
        sub.undeclare()
        z.close()
