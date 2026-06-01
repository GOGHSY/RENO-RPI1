import struct
from pymodbus.exceptions import ModbusException


class TurbiditySensor:
    def __init__(self, client, unit_id=4):
        self.client = client
        self.unit_id = unit_id

    def read_ntu(self):
        try:
            result = self.client.read_holding_registers(
                address=0,
                count=2,
                device_id=self.unit_id,
            )
            if result.isError():
                raise ModbusException("Error reading turbidity registers")
            r0, r1 = result.registers[0], result.registers[1]
            print(f"Turbidity raw registers: r0={r0:#06x} r1={r1:#06x}")
            # Two registers as big-endian FP32 (AB CD)
            raw = struct.pack('>HH', r0, r1)
            return struct.unpack('>f', raw)[0]
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
