from pymodbus.exceptions import ModbusException

class FlowSensor:
    def __init__(self, client, slave_id=1):
        self.client = client
        self.slave_id = slave_id

    def get_flow_rate(self):
        try:
            result = self.client.read_holding_registers(address=0, count=1, device_id=self.slave_id)
            if result.isError():
                raise ModbusException("Error reading flow register")
            return float(result.registers[0])
        except Exception as e:
            print(f"Error reading flow meter: {e}")
            return 0.0
