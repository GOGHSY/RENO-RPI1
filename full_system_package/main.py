import time
from .hardware.flow_sensor import FlowSensor
from .hardware.solenoid import Solenoid
import RPi.GPIO as GPIO
from .database.victoria_logger import VictoriaMetricsLogger
from .control.manager import ControlManager
from .utils import config
from .hardware.turbidity_meter import TurbiditySensor

def start():
    GPIO.setmode(GPIO.BCM)

    valve_main = Solenoid(config.SOLENOID_1_PIN)
    valve_aux  = Solenoid(config.SOLENOID_2_PIN)
    meter      = FlowSensor(port='/dev/ttyUSB0', slave_id=1)
    logger     = VictoriaMetricsLogger()
    brain      = ControlManager()
    turbidity_sensor = TurbiditySensor()

    print("System Online. Monitoring Dual-Valve Setup...")

    try:
        while True:
            flow      = meter.get_flow_rate()
            turbidity = turbidity_sensor.read_voltage()
            print("RAW VOLTAGE:", turbidity, type(turbidity))

            try:
                turbidity = float(turbidity)
            except (TypeError, ValueError):
                print("Invalid turbidity value:", turbidity)
                turbidity = 0.0

            if brain.should_shutdown(turbidity):
                valve_main.close()
                valve_aux.open()
                status = "ALERT: High Flow"
            else:
                valve_main.open()
                valve_aux.close()
                status = "Normal"

            logger.log(flow, valve_main.is_active, valve_aux.is_active, turbidity, status)
            print(f"flow:{flow} | V1: {valve_main.is_active} | V2: {valve_aux.is_active} | turbidity:{turbidity}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        GPIO.cleanup()
