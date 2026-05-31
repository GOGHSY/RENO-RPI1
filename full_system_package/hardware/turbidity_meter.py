import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

class TurbiditySensor:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, parity='N', stopbits=1, bytesize=8, unit_id=1, register=0):
        """
        Initialize Modbus RTU turbidity sensor over serial.

        Args:
            port: Serial port (e.g. /dev/ttyUSB0)
            baudrate: Baud rate (default 9600)
            parity: Parity — 'N', 'E', or 'O'
            stopbits: Stop bits (1 or 2)
            bytesize: Data bits (default 8)
            unit_id: Slave/unit ID of the device
            register: Holding register address for turbidity data
        """
        self.port = port
        self.unit_id = unit_id
        self.register = register
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
        )
        self._connect()

    def _connect(self):
        """Establish Modbus RTU serial connection."""
        if not self.client.connect():
            print(f"Warning: could not connect to turbidity sensor on {self.port}")

    def read_voltage(self):
        """
        Read voltage from sensor via Modbus.
        Assumes the register holds a raw ADC value (0–32767 → 0–5V).
        Adjust scaling to match your device's register map.
        """
        try:
            result = self.client.read_holding_registers(
                address=self.register,
                count=1,
                slave=self.unit_id
            )
            if result.isError():
                raise ModbusException(f"Error reading register {self.register}")

            raw = result.registers[0]
            voltage = (raw / 32767.0) * 5.0  # Scale to 0–5V; adjust per your device spec
            return voltage

        except ModbusException as e:
            print(f"Modbus error: {e}")
            self._connect()  # attempt reconnect next cycle
            return None

    def close(self):
        """Close the Modbus connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

