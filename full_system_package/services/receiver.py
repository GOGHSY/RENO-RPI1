import json
import time

import zenoh

from ..database.victoria_logger import VictoriaMetricsLogger

# Zenoh key (same as MQTT topic)
ZENOH_KEY = "reno/water/treatment/010"

# Connect to your router (Pi1)
ZENOH_ROUTER = "tcp/100.96.169.94:7447"  # <-- your IP from zenohd

influx = VictoriaMetricsLogger()


def listener(sample):
    try:
        payload = sample.payload.decode()
        data = json.loads(payload)

        print("\n--- Sensor Data Received ---")
        for key, value in data.items():
            print(f"  {key:<15}: {value}")

        influx.log_treatment(data)
        print("✓ Logged to VictoriaMetrics")

    except Exception as e:
        import traceback

        print(f"Error: {e}")
        traceback.print_exc()


def start_receiver():
    print("Connecting to Zenoh...")
    conf = zenoh.Config()
    conf.insert_json5("connect/endpoints", f'["{ZENOH_ROUTER}"]')
    z = zenoh.open(conf)
    print(f"Subscribed to {ZENOH_KEY}")
    sub = z.declare_subscriber(ZENOH_KEY, listener)
    print("Listening for water treatment data...")
    try:
        while True:
            time.sleep(1)
    finally:
        sub.undeclare()
        z.close()
