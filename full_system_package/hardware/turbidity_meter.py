import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

class TurbiditySensor:
    def __init__(self, host='192.168.1.100', port=502, unit_id=1, register=0):
        """
        Initialize Modbus TCP turbidity sensor.

        Args:
            host: Modbus device IP address
            port: Modbus TCP port (default 502)
            unit_id: Slave/unit ID of the device
            register: Holding register address for turbidity data
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.register = register
        self.client = ModbusTcpClient(host=self.host, port=self.port)
        self._connect()

    def _connect(self):
        """Establish Modbus TCP connection."""
        if not self.client.connect():
            raise ConnectionError(f"Failed to connect to Modbus device at {self.host}:{self.port}")

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
            return None

    def close(self):
        """Close the Modbus connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

