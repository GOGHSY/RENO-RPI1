# Development Guide

## Prerequisites

- Python 3.11+
- A Raspberry Pi with GPIO (or a dev machine with mocked GPIO)
- USB RS-485 adapters connected to Modbus devices (or simulated)
- VictoriaMetrics binary (download from victoriametrics.com)
- `zenohd` router binary

---

## Setup

```bash
git clone <repo>
cd RENO-RPI1

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Running on a Dev Machine (without hardware)

The application imports `RPi.GPIO` and `pymodbus` which require hardware. To iterate on the web UI or logic without a Pi:

1. **Mock RPi.GPIO**: Install the `RPi.GPIO` stub for non-Pi systems, or patch the import in `full_system_package/hardware/solenoid.py` and `full_system_package/main.py`.

2. **Run only the web UI**:
   ```bash
   # Start VictoriaMetrics manually (or use Docker)
   uvicorn water_ui.ui.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Run only the Zenoh router**:
   ```bash
   zenohd
   ```

---

## Configuration Workflow

Hardware pins, serial ports, and Modbus addresses are in `full_system_package/utils/config.py`. Edit this file when:
- Moving sensors to different USB ports
- Changing Modbus slave IDs
- Rewiring GPIO pins

Runtime settings (threshold, dose, relay) are controlled via the web UI and stored in JSON files in the project root. They do not require a code change or restart.

---

## Debugging

### Check VictoriaMetrics is receiving data

```bash
# List all known metric names
curl http://localhost:8428/api/v1/label/__name__/values

# Query current flow rate
curl 'http://localhost:8428/api/v1/query?query=filtration_flow_rate'
```

Or use the dashboard's `/api/debug/vm` endpoint.

### Check Zenoh connectivity

```bash
# Verify zenohd is running
lsof -i :7447

# Monitor Zenoh traffic (if zenoh CLI tools are installed)
z_sub --key "reno/water/**"
```

### Check Modbus sensors

```bash
# List USB serial devices
ls /dev/ttyUSB*

# Test Modbus with pymodbus CLI
python3 -c "
from pymodbus.client import ModbusSerialClient
c = ModbusSerialClient('/dev/ttyUSB1', baudrate=9600, parity='N', stopbits=1, bytesize=8)
c.connect()
r = c.read_holding_registers(0, 1, 1)
print(r.registers)
c.close()
"
```

### Check GPIO relay

```bash
# Manually toggle the relay
python3 -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.OUT)
GPIO.output(16, GPIO.LOW)   # ON (active-LOW)
import time; time.sleep(2)
GPIO.output(16, GPIO.HIGH)  # OFF
GPIO.cleanup()
"
```

### Logs

The application uses Python `logging` at INFO level. Run with:
```bash
python run.py 2>&1 | tee wtp.log
```

Log format:
```
2026-06-27 10:00:01 [INFO ] __main__: VictoriaMetrics running (pid 12345)
2026-06-27 10:00:03 [INFO ] full_system_package.main: flow=12.50 | turbidity=3.45 | V1=ON V2=OFF | alum=2.50 mL/min
```

---

## Build Process

No build step. Python runs directly from source.

---

## Testing

There are currently **no automated tests**. Manual testing procedure:

1. Start the full system: `python run.py`
2. Open the dashboard at `http://localhost:8000`
3. Verify live metrics update every 2 seconds
4. Test the turbidity threshold by lowering the threshold below the current reading
5. Confirm valve S1 shows CLOSED and S2 shows OPEN in the dashboard
6. Restore the threshold; confirm S1 returns to OPEN
7. Set a relay ON/OFF schedule and confirm the badge cycles between ON/OFF
8. Adjust alum dose and confirm the log line `alum=X.XX mL/min` updates

---

## Coding Conventions

Inferred from the codebase:

- **Logging**: `logging.getLogger(__name__)` at module level; `_log` as the local name. `print()` is not used in production paths (some remain in `receiver.py`).
- **Error handling**: Hardware read failures return safe defaults (`0.0`, `None`) and log at WARNING. Do not raise from sensor reads.
- **GPIO logic**: Relay is active-LOW (LOW = energised). Solenoids are active-HIGH (HIGH = open).
- **File-based state**: Use `Path.write_text(json.dumps(...))` for atomic-ish writes. Use `try/except Exception` with fallback defaults for reads — the file may not exist on first run.
- **Threading**: All spawned threads are daemon threads so they exit automatically when the main thread dies.
- **Zenoh**: Create sessions lazily and recreate on failure (`_get_alum_publisher()` pattern).

---

## Dependency Notes

| Package | Purpose | Notes |
|---|---|---|
| `RPi.GPIO` | GPIO control | Pi-only; requires root or `gpio` group membership |
| `pymodbus` | Modbus RS-485 | Uses `ModbusSerialClient` from pymodbus v3+ API |
| `zenoh` | Pub/sub messaging | Native Python bindings |
| `fastapi` + `uvicorn` | Web server | Async; `lifespan` used for Zenoh init |
| `pyngrok` | Optional ngrok tunnel | Only used if `NGROK_AUTHTOKEN` is set |

---

## Adding a New Sensor

1. Create a driver in `full_system_package/hardware/` following the pattern of `FlowSensor` or `TurbiditySensor`.
2. Instantiate it in `full_system_package/main.py:start()`.
3. Read it in the main loop and pass values to `VictoriaMetricsLogger.log()` (or a new log method).
4. Add the new VictoriaMetrics metric name to `ALL_METRICS` in `water_ui/ui/main.py`.
5. Add a display element to `water_ui/ui/templates/index.html`.
