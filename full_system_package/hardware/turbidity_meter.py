from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian


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
            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers,
                byteorder=Endian.BIG,
                wordorder=Endian.BIG,
            )
            return decoder.decode_32bit_float()
        except Exception as e:
            print(f"Modbus error: {e}")
            return None
