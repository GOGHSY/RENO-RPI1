import json
import logging
import time
import threading

import RPi.GPIO as GPIO
from pymodbus.client import ModbusSerialClient

import shared_state
import zenoh

from .control.manager import ControlManager
from .database.victoria_logger import VictoriaMetricsLogger
from .hardware.flow_sensor import FlowSensor
from .hardware.solenoid import Solenoid
from .hardware.turbidity_meter import TurbiditySensor
from .utils import config

_log = logging.getLogger(__name__)

STOCK_MG_PER_ML = 50.0

_alum_session = None
_alum_pub     = None


def _get_dose_ratio() -> float:
    data = shared_state.read_json(shared_state.DOSE_STATE_FILE, {"dose_mg_per_l": 10.0})
    return data["dose_mg_per_l"] / STOCK_MG_PER_ML


def _get_relay_config() -> tuple:
    data = shared_state.read_json(shared_state.RELAY_STATE_FILE, {
        "enabled": False, "on_duration_seconds": 60.0, "off_duration_seconds": 300.0,
    })
    return bool(data["enabled"]), float(data["on_duration_seconds"]), float(data["off_duration_seconds"])


def _relay_timer_thread() -> None:
    while True:
        enabled, on_dur, off_dur = _get_relay_config()
        if enabled and on_dur > 0 and off_dur > 0:
            _log.info("Relay ON for %.0fs", on_dur)
            GPIO.output(config.RELAY_PIN, GPIO.LOW)
            shared_state.set_relay_on(True)
            time.sleep(on_dur)
            GPIO.output(config.RELAY_PIN, GPIO.HIGH)
            shared_state.set_relay_on(False)
            _log.info("Relay OFF for %.0fs", off_dur)
            end = time.monotonic() + off_dur
            while time.monotonic() < end:
                time.sleep(0.5)
        else:
            GPIO.output(config.RELAY_PIN, GPIO.HIGH)
            shared_state.set_relay_on(False)
            time.sleep(1.0)


def _get_alum_publisher():
    global _alum_session, _alum_pub
    if _alum_pub is not None:
        return _alum_pub
    try:
        conf = zenoh.Config()
        conf.insert_json5("connect/endpoints", '["tcp/127.0.0.1:7447"]')
        _alum_session = zenoh.open(conf)
        _alum_pub = _alum_session.declare_publisher("reno/water/alum/pump")
    except Exception as e:
        _log.warning("Could not create alum Zenoh publisher: %s", e)
    return _alum_pub


def _make_modbus_client(port: str) -> ModbusSerialClient:
    return ModbusSerialClient(
        port=port,
        baudrate=config.MODBUS_BAUDRATE,
        parity="N",
        stopbits=1,
        bytesize=8,
    )


def start() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    flow_client = _make_modbus_client(config.FLOW_PORT)
    if not flow_client.connect():
        _log.warning("Could not connect to flow meter on %s", config.FLOW_PORT)

    turbidity_client = _make_modbus_client(config.TURBIDITY_PORT)
    if not turbidity_client.connect():
        _log.warning("Could not connect to turbidity meter on %s", config.TURBIDITY_PORT)

    GPIO.setup(config.RELAY_PIN, GPIO.OUT)
    GPIO.output(config.RELAY_PIN, GPIO.HIGH)
    threading.Thread(target=_relay_timer_thread, daemon=True).start()

    valve_main       = Solenoid(config.SOLENOID_1_PIN)
    valve_aux        = Solenoid(config.SOLENOID_2_PIN)
    meter            = FlowSensor(client=flow_client, slave_id=config.FLOW_SLAVE_ID)
    turbidity_sensor = TurbiditySensor(client=turbidity_client, unit_id=config.TURBIDITY_SLAVE_ID)
    logger           = VictoriaMetricsLogger()
    brain            = ControlManager()

    _log.info("System online — monitoring dual-valve filtration")

    last_turbidity = None

    try:
        while True:
            flow      = meter.get_flow_rate()
            turbidity = turbidity_sensor.read_voltage()

            if turbidity is not None:
                last_turbidity = float(turbidity)

            turbidity_for_control = last_turbidity if last_turbidity is not None else 0.0

            if brain.should_shutdown(turbidity_for_control):
                valve_main.close()
                valve_aux.open()
                status = "ALERT: High Turbidity"
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

            logger.log(flow, valve_main.is_active, valve_aux.is_active, last_turbidity, status)
            _log.info(
                "flow=%.2f | turbidity=%s | V1=%s V2=%s | alum=%.2f mL/min",
                flow,
                f"{last_turbidity:.2f}" if last_turbidity is not None else "—",
                "ON" if valve_main.is_active else "OFF",
                "ON" if valve_aux.is_active else "OFF",
                ml_per_min,
            )

            time.sleep(1)

    except KeyboardInterrupt:
        _log.info("Stopping sensor loop")
    finally:
        flow_client.close()
        turbidity_client.close()
        GPIO.cleanup()
