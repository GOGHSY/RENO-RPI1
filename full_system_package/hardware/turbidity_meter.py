import struct
from pymodbus.exceptions import ModbusException


class TurbiditySensor:
    def __init__(self, client, unit_id=4):
        self.client = client
        self.unit_id = unit_id

    def read_voltage(self):
        try:
            result = self.client.read_holding_registers(
                address=2,
                count=2,
                device_id=self.unit_id,
            )
            if result.isError():
                raise ModbusException("Error reading turbidity registers")
            r0, r1 = result.registers[0], result.registers[1]
            ntu = struct.unpack('>f', struct.pack('>HH', r0, r1))[0]
            return round(ntu, 2)
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
