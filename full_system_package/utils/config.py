# Hardware Pins (BCM)

SOLENOID_1_PIN = 18  # Main Valve
SOLENOID_2_PIN = 17  # Secondary/Diverter Valve
RELAY_PIN = 16       # Interval relay switch (BCM 16 = physical pin 36)

# Modbus RS-485 — separate USB adapters per sensor
# by-id paths used instead of /dev/ttyUSBx because enumeration order isn't
# stable across boots (ttyUSB0/1 kept swapping between the two adapters)
FLOW_PORT = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG02UV64-if00-port0'
TURBIDITY_PORT = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG03LC9E-if00-port0'
MODBUS_BAUDRATE = 9600
FLOW_SLAVE_ID = 1
TURBIDITY_SLAVE_ID = 4

# VictoriaMetrics
VM_URL = "http://127.0.0.1:8428"
