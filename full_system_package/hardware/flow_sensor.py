import logging

from pymodbus.exceptions import ModbusException

_log = logging.getLogger(__name__)


class FlowSensor:
    def __init__(self, client, slave_id: int = 1):
        self.client   = client
        self.slave_id = slave_id

    def get_flow_rate(self) -> float:
        try:
            result = self.client.read_holding_registers(
                address=0, count=1, device_id=self.slave_id
            )
            if result.isError():
                raise ModbusException("Error reading flow register")
            return float(result.registers[0])
        except Exception as e:
            _log.warning("Flow meter read failed: %s", e)
            return 0.0
