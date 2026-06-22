import logging
import struct

from pymodbus.exceptions import ModbusException

_log = logging.getLogger(__name__)


class TurbiditySensor:
    def __init__(self, client, unit_id: int = 4):
        self.client  = client
        self.unit_id = unit_id

    def read_voltage(self) -> float | None:
        try:
            result = self.client.read_holding_registers(
                address=2, count=2, device_id=self.unit_id
            )
            if result.isError():
                raise ModbusException("Error reading turbidity registers")
            r0, r1 = result.registers[0], result.registers[1]
            ntu = struct.unpack(">f", struct.pack(">HH", r0, r1))[0]
            return round(ntu, 2)
        except Exception as e:
            _log.warning("Turbidity read failed: %s", e)
            return None
