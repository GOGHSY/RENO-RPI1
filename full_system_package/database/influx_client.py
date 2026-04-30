from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from ..utils import config

class InfluxLogger:
    def __init__(self):
        self.client = InfluxDBClient(
            url=config.INFLUX_URL, 
            token=config.INFLUX_TOKEN, 
            org=config.INFLUX_ORG
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def log(self, flow, v1_state, v2_state, turbidity, status):
        """Logs filtration system data (flow, valves, turbidity)"""
        point = Point("filtration") \
            .field("flow_rate",      float(flow)) \
            .field("valve_1_active", 1 if v1_state == "OPEN" else 0) \
            .field("valve_2_active", 1 if v2_state == "OPEN" else 0) \
            .field("turbidity",      float(turbidity)) \
            .tag("status",           str(status))
        self.write_api.write(bucket=config.INFLUX_BUCKET, org=config.INFLUX_ORG, record=point)

    def log_treatment(self, data):
        """
        Dynamically logs all sensor node data to InfluxDB.
        
        Numeric fields  → stored as float fields  (queryable in Grafana)
        String fields   → stored as string fields
        pump1_state     → stored as a tag         (use for filtering in Grafana)
        timestamp       → used as the point time  (aligns with real capture time)
        """
        point = Point("water_treatment")

        # These are handled specially, not as generic fields
        SKIP_KEYS = {"timestamp", "pump1_state"}
        TAG_KEYS  = {"pump1_state"}

        # Attach tags (great for Grafana filtering/grouping)
        for key in TAG_KEYS:
            if key in data:
                point = point.tag(key, str(data[key]))

        # Dynamically attach all sensor readings as fields
        for key, value in data.items():
            if key in SKIP_KEYS:
                continue
            try:
                point = point.field(key, float(value))
            except (ValueError, TypeError):
                point = point.field(key, str(value))  # fallback for non-numeric

        # Use the sensor's own timestamp instead of server arrival time
        if "timestamp" in data:
            try:
                ts = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S.%f")
                point = point.time(ts, WritePrecision.MS)
            except ValueError:
                pass  # falls back to InfluxDB server time if format changes

        self.write_api.write(bucket=config.INFLUX_BUCKET, org=config.INFLUX_ORG, record=point)
        print(f"✓ Logged {len(data)} fields to InfluxDB")
