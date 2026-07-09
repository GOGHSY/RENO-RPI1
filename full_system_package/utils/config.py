# Hardware Pins (BCM)

SOLENOID_1_PIN = 18  # Main Valve
SOLENOID_2_PIN = 17  # Secondary/Diverter Valve
RELAY_PIN = 16       # Interval relay switch (BCM 16 = physical pin 36)

# Modbus RS-485 — separate USB adapters per sensor
FLOW_PORT = '/dev/ttyUSB1'
TURBIDITY_PORT = '/dev/ttyUSB2'
MODBUS_BAUDRATE = 9600
FLOW_SLAVE_ID = 1
TURBIDITY_SLAVE_ID = 4

# VictoriaMetrics
VM_URL = "http://127.0.0.1:8428"
