# Components

## `run.py` — Orchestrator

**Purpose**: Top-level entry point. Starts infrastructure subprocesses, spawns service threads, then hands control to the sensor loop.

**Responsibilities**:
- Launch VictoriaMetrics binary (checks port 8428 first, avoids double-start)
- Launch `zenohd` router (checks port 7447)
- Spawn the Zenoh receiver daemon thread
- Spawn the Uvicorn web server daemon thread
- Attempt Tailscale Funnel → ngrok fallback for public URL
- Call `start()` on the main thread (blocking)
- Gracefully terminate all subprocesses on exit (`stop_all`)

**Key functions**:

| Function | Description |
|---|---|
| `port_open(port)` | TCP connect test — returns True if something is listening |
| `launch(name, cmd)` | Start a subprocess, wait 1s, report success or immediate crash |
| `stop_all()` | Terminate + wait (5s timeout, then kill) all launched subprocesses |
| `run_ui()` | Runs uvicorn in the calling thread |
| `_resolve_public_url()` | Try Tailscale Funnel, fall back to ngrok, return URL or None |

**Dependencies**: `full_system_package`, `water_ui.ui.main`, `uvicorn`, `pyngrok` (optional)

---

## `full_system_package/main.py` — Sensor Loop

**Purpose**: The hardware control brain. Runs the 1-second sensor loop, manages the relay timer thread, and publishes alum dose to Zenoh.

**Responsibilities**:
- Initialise GPIO (BCM mode, no warnings)
- Open Modbus connections to both sensors
- Configure relay GPIO pin and start relay timer thread
- Instantiate all hardware and logic objects
- Poll sensors every second; decide valve positions; log to VictoriaMetrics

**Key functions / values**:

| Symbol | Description |
|---|---|
| `start()` | Public entry point — called by `run.py`; blocks until KeyboardInterrupt |
| `_relay_timer_thread()` | Daemon thread: reads `relay_state.json`, drives GPIO 16 in ON/OFF cycle |
| `_get_alum_publisher()` | Lazy-init Zenoh session + publisher for `reno/water/alum/pump`; recreates on failure |
| `_get_dose_ratio()` | Reads `dose_state.json`, returns `dose_mg_per_l / 50.0` |
| `_get_relay_config()` | Reads `relay_state.json`, returns `(enabled, on_dur, off_dur)` |
| `_make_modbus_client(port)` | Creates `ModbusSerialClient` at 9600-8N1 |
| `STOCK_MG_PER_ML = 50.0` | Alum stock concentration (50,000 mg/L = 50 mg/mL) |

**Key files read at runtime** (re-read every loop iteration or relay cycle):
- `relay_state.json` — relay config
- `dose_state.json` — alum dose

---

## `full_system_package/control/manager.py` — ControlManager

**Purpose**: Encapsulates the single turbidity-based valve control decision.

**Public interface**:

```python
class ControlManager:
    def should_shutdown(self, turbidity: float) -> bool
        # Returns True (ALERT) if turbidity > shared_state.get_threshold()
        # Side effect: updates self.v1_state, self.v2_state strings
```

**Dependencies**: `shared_state` (reads threshold from file each call)

**Notes**: The threshold is read from disk on every call (via `shared_state.get_threshold`), so changes made via the web UI take effect immediately without restarting.

---

## `full_system_package/hardware/flow_sensor.py` — FlowSensor

**Purpose**: Reads instantaneous flow rate from an RS-485 Modbus flow meter.

**Public interface**:

```python
class FlowSensor:
    def __init__(self, client: ModbusSerialClient, slave_id: int = 1)
    def get_flow_rate(self) -> float   # returns 0.0 on error
```

**Protocol**: Reads 1 holding register at address 0, Modbus device ID = slave_id. Returns the raw register value as a float (units are L/min per the sensor datasheet).

---

## `full_system_package/hardware/turbidity_meter.py` — TurbiditySensor

**Purpose**: Reads turbidity (NTU) from an RS-485 Modbus turbidity meter that encodes the value as an IEEE 754 32-bit float split across two 16-bit registers.

**Public interface**:

```python
class TurbiditySensor:
    def __init__(self, client: ModbusSerialClient, unit_id: int = 4)
    def read_voltage(self) -> float | None   # returns None on error
```

**Protocol**: Reads 2 holding registers at address 2, device ID = unit_id. Decodes as big-endian float:
```python
ntu = struct.unpack(">f", struct.pack(">HH", r0, r1))[0]
```

Note: the method is named `read_voltage` for historical reasons; it actually returns NTU.

---

## `full_system_package/hardware/solenoid.py` — Solenoid

**Purpose**: Abstraction over a GPIO-driven solenoid valve.

**Public interface**:

```python
class Solenoid:
    def __init__(self, pin: int = 18)
    def open(self) -> None    # GPIO HIGH
    def close(self) -> None   # GPIO LOW
    @property
    def is_active(self) -> bool   # reads current GPIO state
```

**Notes**: Constructor calls `close()` immediately, so both valves start in the closed (safe) position.

---

## `full_system_package/database/victoria_logger.py` — VictoriaMetricsLogger

**Purpose**: Writes sensor data to VictoriaMetrics using InfluxDB line protocol.

**Public interface**:

```python
class VictoriaMetricsLogger:
    def log(self, flow, v1_state, v2_state, turbidity, status) -> None
    def log_treatment(self, data: dict) -> None
```

**`log()`** writes a `filtration` measurement:
```
filtration,status=Normal flow_rate=12.5,valve_1_active=1,valve_2_active=0,turbidity=3.45
```

**`log_treatment()`** writes a `water_treatment` measurement from an arbitrary dict (RPi2 data). Tags: `pump1_state`. Fields: all numeric values.

**Retry logic**: `_send()` retries up to 3 times with a 2-second timeout per attempt.

---

## `full_system_package/services/receiver.py` — Zenoh Receiver

**Purpose**: Subscribes to RPi2's chemical-treatment sensor data via Zenoh and logs it to VictoriaMetrics.

**Key constants**:

| Constant | Value |
|---|---|
| `ZENOH_KEY` | `reno/water/treatment/010` |
| `ZENOH_ROUTER` | `tcp/100.96.169.94:7447` |

**`listener(sample)`**: Decodes JSON payload, prints all key-value pairs, calls `VictoriaMetricsLogger.log_treatment()`.

**`start_receiver()`**: Opens Zenoh session, declares subscriber, loops forever with `time.sleep(1)`.

---

## `full_system_package/utils/config.py` — Configuration

**Purpose**: Central location for all hardware constants. No logic — pure constants.

| Constant | Value | Notes |
|---|---|---|
| `SOLENOID_1_PIN` | 18 | BCM GPIO |
| `SOLENOID_2_PIN` | 17 | BCM GPIO |
| `RELAY_PIN` | 16 | BCM GPIO (physical pin 36) |
| `FLOW_PORT` | `/dev/ttyUSB1` | RS-485 adapter |
| `TURBIDITY_PORT` | `/dev/ttyUSB2` | RS-485 adapter |
| `MODBUS_BAUDRATE` | 9600 | 8N1 |
| `FLOW_SLAVE_ID` | 1 | Modbus device address |
| `TURBIDITY_SLAVE_ID` | 4 | Modbus device address |
| `VM_URL` | `http://127.0.0.1:8428` | VictoriaMetrics endpoint |

---

## `shared_state.py` — Shared State

**Purpose**: Thread-safe state shared between the hardware loop, relay timer, and web server.

**State 1: relay_on** (in-memory, `threading.Lock`):
```python
def get_relay_on() -> bool
def set_relay_on(val: bool) -> None
```
Written by `_relay_timer_thread`; read by the web UI's `/api/live` endpoint.

**State 2: turbidity_threshold** (file-backed JSON, `threshold_state.json`):
```python
def get_threshold() -> float     # reads from file each call
def set_threshold(val: float) -> None   # writes to file
```
Written by the web UI; read by `ControlManager.should_shutdown()` on each sensor-loop iteration.

---

## `water_ui/ui/main.py` — FastAPI Application

**Purpose**: Web server providing the dashboard UI and REST API.

**Authentication**: HTTP Basic Auth middleware (every request). Credentials from `WTP_USER`/`WTP_PASS` env vars (defaults: `admin` / `reno@123`).

**Lifespan**: On startup, opens a Zenoh session and declares a publisher on key `water/control`.

**State files read/written**:
- `dose_state.json` (3 levels up)
- `relay_state.json` (2 levels up)

See [API.md](API.md) for the full endpoint reference.

**VictoriaMetrics query URLs**:
- Instant: `http://localhost:8428/api/v1/query`
- Range: `http://localhost:8428/api/v1/query_range`

**`ALL_METRICS` dict**: Maps dashboard keys (`flow_rate`, `turbidity`, `pH1`, …) to VictoriaMetrics metric names. Both RPi1 and RPi2 metrics are served from the same dashboard.

---

## `water_ui/ui/templates/index.html` — Dashboard SPA

**Purpose**: Single-page application with three views — Live, History, Table.

**Live view**:
- Polls `/api/live` every 2 seconds
- Shows sparkline charts (80-point ring buffer, Chart.js)
- Turbidity threshold setter, relay config, alum dose control

**History view**:
- Fetches `/api/range` for each metric with auto-selected step
- Chart.js time-series charts with date-fns adapter

**Table view**:
- Fetches `/api/table` (paginated, 100 rows/page, newest first)
- Colour-coded columns: blue = RPi1, purple = RPi2

**CSV download**: `GET /api/download?start=&end=` — auto step, all metrics.

**External dependencies** (CDN):
- `chart.js@4.4.0`
- `chartjs-adapter-date-fns@3.0.0`

