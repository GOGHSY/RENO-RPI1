# Hardware Pins (BCM)

FLOW_SENSOR_PIN = 21
SOLENOID_1_PIN = 18  # Main Valve
SOLENOID_2_PIN = 17  # Secondary/Diverter Valve
RELAY_PIN = 3        # Interval relay switch

# Modbus RS-485 — separate USB adapters per sensor
FLOW_PORT = '/dev/ttyUSB1'
TURBIDITY_PORT = '/dev/ttyUSB2'
MODBUS_BAUDRATE = 9600
FLOW_SLAVE_ID = 1
TURBIDITY_SLAVE_ID = 4

# InfluxDB 2.x Settings
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "C53KoqRvDb1ZfBLq3WEYCSck5AIPZv5Kiac9G66Pi1P5gDj5PWjGCp2VTNf5HBPGCPgPdwU7JVH9rCK0FRc6bA=="
INFLUX_ORG = "water_quality_iot"
INFLUX_BUCKET = "IOT"

# Logic Thresholds
FLOW_THRESHOLD = 15.0  # L/min

# victoriametrics
VM_URL = "http://127.0.0.1:8428"
