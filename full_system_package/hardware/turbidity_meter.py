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

            # Scan registers 0-15 to find where 73.85 NTU is stored
            scan = self.client.read_holding_registers(address=0, count=16, device_id=self.unit_id)
            if not scan.isError():
                for i in range(0, 15, 2):
                    r0, r1 = scan.registers[i], scan.registers[i+1]
                    try:
                        val_be = struct.unpack('>f', struct.pack('>HH', r0, r1))[0]
                        val_le = struct.unpack('>f', struct.pack('>HH', r1, r0))[0]
                        print(f"  reg[{i},{i+1}] = {r0:#06x},{r1:#06x} | BE={val_be:.2f} LE={val_le:.2f}")
                    except Exception:
                        pass

            return 0.0
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
