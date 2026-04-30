import minimalmodbus
from ..utils import config

class FlowSensor:
    def __init__(self, port='/dev/ttyUSB0', slave_id=1):
        self.instrument = minimalmodbus.Instrument(port, slave_id)
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.timeout = 1
        print(f"Modbus Flow Meter initialized on {port}")

    def get_flow_rate(self):
        try:
            # Using the logic from your image: register 0, function code 3
            value = self.instrument.read_register(0, number_of_decimals=0, functioncode=3)
            return float(value)
        except Exception as e:
            print(f"Error reading Modbus meter: {e}")
            return 0.0
