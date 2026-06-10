import struct
from pymodbus.exceptions import ModbusException


class TurbiditySensor:
    def __init__(self, client, unit_id=4):
        self.client = client
        self.unit_id = unit_id

    def read_voltage(self):
        try:
            for label, fn in [("INPUT(FC04)", self.client.read_input_registers),
                               ("HOLDING(FC03)", self.client.read_holding_registers)]:
                scan = fn(address=0, count=16, device_id=self.unit_id)
                if scan.isError():
                    print(f"  {label}: error")
                    continue
                print(f"  {label} scan:")
                for i in range(0, 16, 2):
                    r0, r1 = scan.registers[i], scan.registers[i + 1]
                    try:
                        val_be = struct.unpack('>f', struct.pack('>HH', r0, r1))[0]
                        val_le = struct.unpack('>f', struct.pack('>HH', r1, r0))[0]
                        print(f"    reg[{i},{i+1}] = {r0:#06x},{r1:#06x} | BE={val_be:.4f} LE={val_le:.4f} | raw={r0}")
                    except Exception:
                        pass
            return 0.0
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
