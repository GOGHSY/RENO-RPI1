# Database

## VictoriaMetrics

VictoriaMetrics is the sole time-series database. It is launched by `run.py` as a subprocess on the same Pi.

| Setting | Value |
|---|---|
| Binary | `/home/suprabha/victoria-metrics-prod` |
| HTTP port | `8428` |
| Data directory | `/home/suprabha/victoria-metrics-data` |
| Write protocol | InfluxDB line protocol (`POST /write`) |
| Query protocol | Prometheus/MetricsQL (`/api/v1/query`, `/api/v1/query_range`) |

---

## Measurements

### `filtration`

Written by `VictoriaMetricsLogger.log()` on every sensor-loop iteration (~1 Hz).

**Tags**:

| Tag | Example values |
|---|---|
| `status` | `Normal`, `ALERT:\ High\ Turbidity` |

**Fields**:

| Field | Type | Units | Description |
|---|---|---|---|
| `flow_rate` | float | L/min | Raw flow meter reading |
| `valve_1_active` | int (0/1) | — | Main solenoid state |
| `valve_2_active` | int (0/1) | — | Aux/diverter solenoid state |
| `turbidity` | float | NTU | Turbidity (omitted if sensor read failed) |

**Example line**:
```
filtration,status=Normal flow_rate=12.5,valve_1_active=1,valve_2_active=0,turbidity=3.45
```

VictoriaMetrics stores this as individual metrics:
- `filtration_flow_rate`
- `filtration_valve_1_active`
- `filtration_valve_2_active`
- `filtration_turbidity`

---

### `water_treatment`

Written by `VictoriaMetricsLogger.log_treatment()` when RPi2 data arrives via Zenoh.

**Tags** (when present in incoming dict):

| Tag | Description |
|---|---|
| `pump1_state` | String state of Pump 1 |

**Fields**: All other numeric values from the RPi2 JSON payload. Typical fields:

| Field | Units | Description |
|---|---|---|
| `ORP` | mV | Oxidation-Reduction Potential, pre rapid-mix |
| `pH1` | pH | Pre rapid-mix |
| `pH2` | pH | Post flocculation |
| `pH3` | pH | Post sedimentation |
| `RTD1` | °C | Temperature, pre rapid-mix |
| `RTD2` | °C | Temperature, pre rapid-mix (secondary) |
| `RTD3` | °C | Temperature, post flocculation |
| `RTD4` | °C | Temperature, effluent |
| `EC` | µS/cm | Electrical conductivity, post lime |
| `Pump1` | — | Alum dosing pump duty / rate |
| `Pump2` | — | Lime dosing pump duty / rate |

---

## JSON State Files

These are not a database but serve as persistent configuration. They are read and written directly by the application.

### `threshold_state.json`

```json
{"turbidity_threshold": 10.0}
```

Written by `shared_state.set_threshold()`; read by `shared_state.get_threshold()`. Controls the turbidity alarm level (NTU).

### `dose_state.json`

```json
{"dose_mg_per_l": 10.0}
```

Written by `POST /alum/dose`; read by `full_system_package/main.py:_get_dose_ratio()`. Controls alum coagulant dosing.

### `relay_state.json`

```json
{
  "enabled": true,
  "on_duration_seconds": 120.0,
  "off_duration_seconds": 600.0
}
```

Written by `POST /relay/config`; read by `_relay_timer_thread()`. Controls the relay switch duty cycle.

---

## Data Retention

VictoriaMetrics defaults to storing data indefinitely (no built-in TTL unless configured with `-retentionPeriod`). The current launch command does not set a retention period.
