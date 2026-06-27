# RENO-RPI1 — Water Treatment Filtration Controller

**RENO-RPI1** is the filtration-system controller for a two-Raspberry-Pi water treatment plant (WTP) monitoring and control system. Running on **RPi1**, it reads a flow meter and turbidity sensor via Modbus RS-485, drives two solenoid valves and a relay switch via GPIO, calculates alum dosing rates, and exposes a real-time web dashboard backed by VictoriaMetrics.

A companion device (**RPi2**) handles chemical-treatment sensors (pH, ORP, RTD, EC, dosing pumps). The two Pis communicate over **Zenoh** pub/sub messaging.

---

## Features

- Real-time flow-rate and turbidity monitoring (Modbus RS-485)
- Automatic solenoid valve switching on turbidity alarm
- Configurable alum coagulant dosing — dose rate published to RPi2 via Zenoh
- Relay switch with configurable ON/OFF duty cycle (e.g. for a chemical feed pump)
- VictoriaMetrics time-series storage with InfluxDB line-protocol writes
- FastAPI web dashboard — live metrics, historical charts, tabular data, CSV export
- HTTP Basic Auth with env-var overrides
- Optional public URL via Tailscale Funnel or ngrok

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Web framework | FastAPI + Uvicorn |
| Messaging | Zenoh (pub/sub, replaces MQTT) |
| Modbus | pymodbus (RS-485 serial) |
| GPIO | RPi.GPIO |
| Time-series DB | VictoriaMetrics (InfluxDB line protocol) |
| Frontend | Vanilla JS + Chart.js 4 |
| Templating | Jinja2 |
| Tunnel | Tailscale Funnel / pyngrok |

---

## Hardware

| Item | GPIO / Port | Notes |
|---|---|---|
| Solenoid 1 — Main Valve | BCM 18 | HIGH = open |
| Solenoid 2 — Aux/Diverter | BCM 17 | HIGH = open |
| Relay switch | BCM 16 (pin 36) | Active-LOW module — LOW = energised |
| Flow meter | `/dev/ttyUSB1` | Modbus slave 1, register 0 |
| Turbidity sensor | `/dev/ttyUSB2` | Modbus slave 4, registers 2-3 (IEEE 754 float) |

---

## Installation

### Prerequisites

- Raspberry Pi (or compatible Linux board) with Python 3.11+
- VictoriaMetrics binary at `/home/suprabha/victoria-metrics-prod`
- `zenohd` router at `/usr/local/bin/zenohd`
- USB RS-485 adapters connected to flow meter and turbidity sensor

### Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` installs: `RPi.GPIO`, `zenoh`, `pymodbus`, `fastapi`, `uvicorn[standard]`, `Jinja2`, `requests`, `pyngrok`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WTP_USER` | `admin` | Dashboard HTTP Basic Auth username |
| `WTP_PASS` | `reno@123` | Dashboard HTTP Basic Auth password |
| `NGROK_AUTHTOKEN` | _(none)_ | If set, ngrok tunnel is opened on port 8000 |

---

## Running Locally

```bash
python run.py
```

`run.py` starts everything in the correct order:

1. VictoriaMetrics on `localhost:8428`
2. Zenoh router on `localhost:7447`
3. Zenoh receiver thread (RPi2 data ingest)
4. Uvicorn web server on `0.0.0.0:8000`
5. Tailscale Funnel or ngrok (if available)
6. The blocking sensor-control loop

Open `http://<pi-ip>:8000` in a browser.

---

## Configuration

Hardware pin assignments and serial ports live in `full_system_package/utils/config.py`. Edit this file to match your wiring:

```python
SOLENOID_1_PIN = 18   # Main valve
SOLENOID_2_PIN = 17   # Aux/diverter valve
RELAY_PIN      = 16   # Interval relay
FLOW_PORT      = '/dev/ttyUSB1'
TURBIDITY_PORT = '/dev/ttyUSB2'
```

Runtime settings are persisted to JSON files in the project root:

| File | Contents |
|---|---|
| `threshold_state.json` | Turbidity alarm threshold (NTU) |
| `dose_state.json` | Alum dose target (mg/L) |
| `relay_state.json` | Relay ON/OFF durations and enabled flag |

These files are written by the web UI and read by the sensor loop in real-time — no restart required.

---

## Build / Deployment

There is no build step. The project runs directly from source. For production deployment, create a `systemd` unit:

```ini
[Unit]
Description=RENO RPi1 Water Treatment Controller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/RENO-RPI1/run.py
WorkingDirectory=/path/to/RENO-RPI1
Restart=on-failure
Environment=WTP_USER=admin WTP_PASS=reno@123

[Install]
WantedBy=multi-user.target
```

---

## Testing

There is no automated test suite. Testing is done manually on hardware. See [DEVELOPMENT.md](DEVELOPMENT.md) for the debug workflow.

---

## Project Structure

```
RENO-RPI1/
├── run.py                          # Entry point — orchestrates all services
├── shared_state.py                 # Thread-safe relay status + turbidity threshold
├── requirements.txt
│
├── full_system_package/            # Hardware control package
│   ├── main.py                     # Sensor loop + valve/relay control
│   ├── control/
│   │   └── manager.py              # ControlManager — turbidity alarm logic
│   ├── database/
│   │   └── victoria_logger.py      # VictoriaMetrics write client
│   ├── hardware/
│   │   ├── flow_sensor.py          # FlowSensor — Modbus RS-485
│   │   ├── solenoid.py             # Solenoid — GPIO output
│   │   └── turbidity_meter.py      # TurbiditySensor — Modbus RS-485 (float)
│   ├── services/
│   │   └── receiver.py             # Zenoh subscriber for RPi2 treatment data
│   └── utils/
│       └── config.py               # Hardware constants
│
└── water_ui/
    └── ui/
        ├── main.py                 # FastAPI app — REST API + dashboard
        └── templates/
            └── index.html          # Single-page dashboard (Chart.js)
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set credentials (optional)
export WTP_USER=operator WTP_PASS=mysecret

# 3. Run
python run.py

# 4. Open dashboard
open http://localhost:8000
```
