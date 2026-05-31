from pymodbus.exceptions import ModbusException

class TurbiditySensor:
    def __init__(self, client, unit_id=2, register=0):
        self.client = client
        self.unit_id = unit_id
        self.register = register

    def read_voltage(self):
        try:
            result = self.client.read_holding_registers(
                address=self.register,
                count=1,
                device_id=self.unit_id,
            )
            if result.isError():
                raise ModbusException(f"Error reading register {self.register}")
            raw = result.registers[0]
            voltage = (raw / 32767.0) * 5.0  # 0–32767 → 0–5 V; adjust per device spec
            return voltage
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
