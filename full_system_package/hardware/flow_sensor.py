import minimalmodbus
from ..utils import config

class FlowSensor:
    def __init__(self, port='/dev/ttyUSB0', slave_id=1):
        self.port = port
        self.slave_id = slave_id
        self.instrument = None
        self._connect()

    def _connect(self):
        try:
            self.instrument = minimalmodbus.Instrument(self.port, self.slave_id)
            self.instrument.serial.baudrate = 9600
            self.instrument.serial.timeout = 1
            print(f"Modbus Flow Meter initialized on {self.port}")
        except Exception as e:
            print(f"Flow sensor not available on {self.port}: {e}")
            self.instrument = None

    def get_flow_rate(self):
        if self.instrument is None:
            self._connect()
        if self.instrument is None:
            return 0.0
        try:
            value = self.instrument.read_register(0, number_of_decimals=0, functioncode=3)
            return float(value)
        except Exception as e:
            print(f"Error reading Modbus meter: {e}")
            self.instrument = None  # force reconnect next cycle
            return 0.0
