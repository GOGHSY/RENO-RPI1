import json
import time
import threading
from pathlib import Path
from pymodbus.client import ModbusSerialClient
from .hardware.flow_sensor import FlowSensor
from .hardware.solenoid import Solenoid
import RPi.GPIO as GPIO
from .database.victoria_logger import VictoriaMetricsLogger
from .control.manager import ControlManager
from .utils import config
from .hardware.turbidity_meter import TurbiditySensor
from .services.receiver import start_receiver
import zenoh

DOSE_STATE_FILE = Path(__file__).resolve().parents[1] / "dose_state.json"
STOCK_MG_PER_ML = 50.0

def _get_dose_ratio() -> float:
    try:
        return json.loads(DOSE_STATE_FILE.read_text())["dose_mg_per_l"] / STOCK_MG_PER_ML
    except Exception:
        return 0.2

_alum_pub = None

def _get_alum_publisher():
    global _alum_pub
    if _alum_pub is not None:
        return _alum_pub
    try:
        session = zenoh.open(zenoh.Config())
        _alum_pub = session.declare_publisher("reno/water/alum/pump")
    except Exception as e:
        print(f"Warning: could not create alum Zenoh publisher: {e}")
    return _alum_pub

def start():
    GPIO.setmode(GPIO.BCM)

    flow_client = ModbusSerialClient(
        port=config.FLOW_PORT,
        baudrate=config.MODBUS_BAUDRATE,
        parity='N',
        stopbits=1,
        bytesize=8,
    )
    if not flow_client.connect():
        print(f"Warning: could not connect to flow meter on {config.FLOW_PORT}")

    turbidity_client = ModbusSerialClient(
        port=config.TURBIDITY_PORT,
        baudrate=config.MODBUS_BAUDRATE,
        parity='N',
        stopbits=1,
        bytesize=8,
    )
    if not turbidity_client.connect():
        print(f"Warning: could not connect to turbidity meter on {config.TURBIDITY_PORT}")

    valve_main = Solenoid(config.SOLENOID_1_PIN)
    valve_aux  = Solenoid(config.SOLENOID_2_PIN)
    meter      = FlowSensor(client=flow_client, slave_id=config.FLOW_SLAVE_ID)
    turbidity_sensor = TurbiditySensor(client=turbidity_client, unit_id=config.TURBIDITY_SLAVE_ID)
    logger     = VictoriaMetricsLogger()
    brain      = ControlManager()

    # Start MQTT receiver in background thread
    receiver_thread = threading.Thread(target=start_receiver, daemon=True)
    receiver_thread.start()
    print("MQTT Receiver started in background...")

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

            ml_per_min = round(flow * _get_dose_ratio(), 2)
            pub = _get_alum_publisher()
            if pub:
                try:
                    pub.put(json.dumps({"ml_per_min": ml_per_min}))
                except Exception:
                    _alum_pub = None

            logger.log(flow, valve_main.is_active, valve_aux.is_active, turbidity, status)
            print(f"flow:{flow} | V1: {valve_main.is_active} | V2: {valve_aux.is_active} | turbidity:{turbidity} | alum:{ml_per_min}mL/min")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        flow_client.close()
        turbidity_client.close()
        GPIO.cleanup()
