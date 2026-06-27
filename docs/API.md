# API Reference

The web dashboard exposes a REST API served by FastAPI on port 8000.

## Authentication

All endpoints require **HTTP Basic Auth**.

| Credential | Default | Override |
|---|---|---|
| Username | `admin` | `WTP_USER` env var |
| Password | `reno@123` | `WTP_PASS` env var |

Unauthenticated requests receive `401` with `WWW-Authenticate: Basic realm="WTP Dashboard"`.

---

## Pages

### `GET /`
Returns the HTML dashboard (single-page application).

**Response**: `200 text/html`

---

## Live Data

### `GET /api/live`
Returns the current value of every metric from VictoriaMetrics plus the relay hardware state.

**Response**:
```json
{
  "flow_rate":  12.4,
  "turbidity":  3.15,
  "valve1":     1.0,
  "valve2":     0.0,
  "ORP":        245.1,
  "pH1":        7.02,
  "pH2":        7.18,
  "pH3":        7.25,
  "RTD1":       22.5,
  "RTD2":       22.3,
  "RTD3":       22.0,
  "RTD4":       21.8,
  "EC":         310.5,
  "Pump1":      1.0,
  "Pump2":      0.0,
  "relay_on":   true
}
```
Any metric unavailable from VictoriaMetrics is `null`. `relay_on` is the live GPIO state from `shared_state`.

---

## Historical Data

### `GET /api/range`
Returns time-series values for a single metric.

**Query parameters**:

| Param | Type | Required | Description |
|---|---|---|---|
| `metric` | string | yes | One of the keys from `ALL_METRICS` (e.g. `flow_rate`, `turbidity`, `pH1`) |
| `start` | int | yes | Unix timestamp (seconds) |
| `end` | int | yes | Unix timestamp (seconds) |
| `step` | string | no | VictoriaMetrics step (default `60s`) |

**Response**:
```json
{
  "values": [
    [1719480000000, 12.4],
    [1719480060000, 12.5]
  ]
}
```
Timestamps are in **milliseconds** (for Chart.js compatibility).

**Error response** (unknown metric):
```json
{"values": [], "error": "Unknown metric"}
```

---

### `GET /api/table`
Returns a paginated time-series table across all metrics.

**Query parameters**:

| Param | Type | Required | Description |
|---|---|---|---|
| `start` | int | yes | Unix timestamp (seconds) |
| `end` | int | yes | Unix timestamp (seconds) |

Step is auto-selected:
- ≤ 1 h → `10s`
- ≤ 24 h → `5m`
- else → `30m`

**Response**:
```json
{
  "columns": ["timestamp_utc", "flow_rate", "turbidity", "valve1", "valve2", "ORP", "pH1", ...],
  "rows": [
    ["2026-06-27 10:00:00", 12.4, 3.15, 1.0, 0.0, 245.1, 7.02, ...],
    ...
  ],
  "total": 360
}
```
Rows are sorted **newest first**.

---

### `GET /api/download`
Streams all metrics as a CSV file.

**Query parameters**:

| Param | Type | Required |
|---|---|---|
| `start` | int | yes |
| `end` | int | yes |

Step auto-selection: same as `/api/table`.

**Response**: `200 text/csv; filename=wtp_data.csv`
```
timestamp_utc,flow_rate,turbidity,valve1,valve2,ORP,pH1,...
2026-06-27 10:00:00,12.4,3.15,1.0,0.0,245.1,7.02,...
```

---

## Valve and Pump Commands

These endpoints publish a Zenoh command to the `water/control` key. They do **not** directly control GPIO — they are intended for a downstream subscriber.

### `POST /valve/open`
Publishes `{"cmd":"valve_open"}`.

**Response**: `{"ok": true}`

### `POST /valve/close`
Publishes `{"cmd":"valve_close"}`.

**Response**: `{"ok": true}`

### `POST /pump/start`
Publishes `{"cmd":"pump_start"}`.

**Response**: `{"ok": true}`

### `POST /pump/stop`
Publishes `{"cmd":"pump_stop"}`.

**Response**: `{"ok": true}`

**503 error**: If Zenoh session is not connected: `{"detail": "Zenoh not connected"}`.

---

## Turbidity Threshold

### `GET /api/threshold`
Returns the current turbidity alarm threshold.

**Response**:
```json
{"value": 10.0}
```

### `POST /api/threshold`
Sets the turbidity alarm threshold. Takes effect immediately (next sensor-loop iteration).

**Request body**:
```json
{"value": 7.5}
```

**Response**: `{"value": 7.5}`

**400 error**: `{"detail": "Threshold must be >= 0"}`

---

## Alum Dosing

### `GET /alum/dose`
Returns the current alum dose setting.

**Response**:
```json
{
  "dose_mg_per_l": 10.0,
  "ratio_ml_per_l": 0.2
}
```
`ratio_ml_per_l` = `dose_mg_per_l / 50.0` (stock concentration 50 mg/mL).

### `POST /alum/dose`
Sets the alum dose target. The sensor loop reads this every second and recalculates the alum pump rate.

**Request body**:
```json
{"dose_mg_per_l": 15.0}
```

**Response**:
```json
{
  "dose_mg_per_l": 15.0,
  "ratio_ml_per_l": 0.3
}
```

**400 error**: `{"detail": "Dose must be positive"}`

---

## Relay Control

### `GET /relay/config`
Returns the relay interval configuration.

**Response**:
```json
{
  "on_duration_seconds": 60.0,
  "off_duration_seconds": 300.0,
  "enabled": true
}
```

### `POST /relay/config`
Updates the relay interval configuration. The relay timer thread reads this on the next cycle.

**Request body**:
```json
{
  "on_duration_seconds": 120.0,
  "off_duration_seconds": 600.0,
  "enabled": true
}
```

**Response**: same shape as request.

**400 errors**: `{"detail": "ON duration must be positive"}` / `{"detail": "OFF duration must be positive"}`

---

## Debug / Health

### `GET /status`
Lightweight health check.

**Response**: `{"system": "running"}`

### `GET /api/debug/vm`
Returns all metric names known to VictoriaMetrics (for troubleshooting missing data).

**Response**: VictoriaMetrics `/api/v1/label/__name__/values` JSON.

---

## Metric Name Mapping

The `ALL_METRICS` dict in `water_ui/ui/main.py` maps API keys to VictoriaMetrics series names:

| API key | VictoriaMetrics name | Source |
|---|---|---|
| `flow_rate` | `filtration_flow_rate` | RPi1 |
| `turbidity` | `filtration_turbidity` | RPi1 |
| `valve1` | `filtration_valve_1_active` | RPi1 |
| `valve2` | `filtration_valve_2_active` | RPi1 |
| `ORP` | `water_treatment_ORP` | RPi2 |
| `pH1` | `water_treatment_pH1` | RPi2 |
| `pH2` | `water_treatment_pH2` | RPi2 |
| `pH3` | `water_treatment_pH3` | RPi2 |
| `RTD1` | `water_treatment_RTD1` | RPi2 |
| `RTD2` | `water_treatment_RTD2` | RPi2 |
| `RTD3` | `water_treatment_RTD3` | RPi2 |
| `RTD4` | `water_treatment_RTD4` | RPi2 |
| `EC` | `water_treatment_EC` | RPi2 |
| `Pump1` | `water_treatment_Pump1` | RPi2 |
| `Pump2` | `water_treatment_Pump2` | RPi2 |
