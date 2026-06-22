import base64
import csv
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import requests
import zenoh
import shared_state
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

VM_URL       = "http://localhost:8428/api/v1/query"
VM_RANGE_URL = "http://localhost:8428/api/v1/query_range"

DOSE_STATE_FILE  = Path(__file__).resolve().parents[3] / "dose_state.json"
RELAY_STATE_FILE = Path(__file__).resolve().parents[2] / "relay_state.json"
STOCK_MG_PER_ML  = 50.0  # 50,000 mg/L stock = 50 mg/mL

def _read_dose() -> float:
    try:
        return json.loads(DOSE_STATE_FILE.read_text())["dose_mg_per_l"]
    except Exception:
        return 10.0

def _write_dose(dose: float) -> None:
    DOSE_STATE_FILE.write_text(json.dumps({"dose_mg_per_l": dose}))

ZENOH_KEY = "water/control"

# ── Auth ───────────────────────────────────────────────────────────────────
# Set WTP_USER / WTP_PASS env vars to change credentials.
# e.g.  export WTP_USER=sem129  WTP_PASS=mypassword
BASIC_USER = os.getenv("WTP_USER", "admin")
BASIC_PASS = os.getenv("WTP_PASS", "reno@123")

if BASIC_USER == "admin" and BASIC_PASS == "sem129wtp":
    print("⚠  Using default credentials. Set WTP_USER and WTP_PASS env vars to change them.")

# Every metric in the system with its VictoriaMetrics name
ALL_METRICS = {
    # RPi1 — Filtration
    "flow_rate":  "filtration_flow_rate",
    "turbidity":  "filtration_turbidity",
    "valve1":     "filtration_valve_1_active",
    "valve2":     "filtration_valve_2_active",
    # RPi2 — Chemical Treatment
    "ORP":   "water_treatment_ORP",
    "pH1":   "water_treatment_pH1",
    "pH2":   "water_treatment_pH2",
    "pH3":   "water_treatment_pH3",
    "RTD1":  "water_treatment_RTD1",
    "RTD2":  "water_treatment_RTD2",
    "RTD3":  "water_treatment_RTD3",
    "RTD4":  "water_treatment_RTD4",
    "EC":    "water_treatment_EC",
    "Pump1": "water_treatment_Pump1",
    "Pump2": "water_treatment_Pump2",
}

_zenoh_session = None
_zenoh_pub = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _zenoh_session, _zenoh_pub
    conf = zenoh.Config()
    _zenoh_session = zenoh.open(conf)
    _zenoh_pub = _zenoh_session.declare_publisher(ZENOH_KEY)
    yield
    if _zenoh_pub:
        _zenoh_pub.undeclare()
    if _zenoh_session:
        _zenoh_session.close()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            user, pw = base64.b64decode(auth[6:]).decode().split(":", 1)
            if (secrets.compare_digest(user, BASIC_USER) and
                    secrets.compare_digest(pw, BASIC_PASS)):
                return await call_next(request)
        except Exception:
            pass
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="WTP Dashboard"'},
    )


def _publish(cmd: str):
    if _zenoh_pub is None:
        raise HTTPException(status_code=503, detail="Zenoh not connected")
    _zenoh_pub.put(cmd.encode())


def _instant(vm_name: str):
    try:
        r = requests.get(VM_URL, params={"query": vm_name}, timeout=2)
        j = r.json()
        if j.get("data") and j["data"]["result"]:
            return float(j["data"]["result"][0]["value"][1])
    except Exception:
        pass
    return None


# ── Pages ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ── Live data ──────────────────────────────────────────────────────────────

@app.get("/api/live")
def get_live():
    """All current metric values in one request."""
    data = {k: _instant(v) for k, v in ALL_METRICS.items()}
    data["relay_on"] = shared_state.get_relay_on()
    return data


# ── Historical range ───────────────────────────────────────────────────────

@app.get("/api/range")
def get_range(metric: str, start: int, end: int, step: str = "60s"):
    vm_name = ALL_METRICS.get(metric)
    if not vm_name:
        return {"values": [], "error": "Unknown metric"}
    try:
        r = requests.get(VM_RANGE_URL, params={
            "query": vm_name, "start": start, "end": end, "step": step,
        }, timeout=10)
        j = r.json()
        if j.get("data") and j["data"]["result"]:
            return {"values": [
                [int(float(v[0])) * 1000, float(v[1])]
                for v in j["data"]["result"][0]["values"]
            ]}
    except Exception as e:
        return {"values": [], "error": str(e)}
    return {"values": []}


# ── CSV download ───────────────────────────────────────────────────────────

@app.get("/api/download")
def download_csv(start: int, end: int):
    duration = end - start
    if duration <= 3600:
        step = "10s"
    elif duration <= 86400:
        step = "5m"
    else:
        step = "30m"

    data: dict[int, dict] = {}
    timestamps: set[int] = set()

    for col, vm_name in ALL_METRICS.items():
        try:
            r = requests.get(VM_RANGE_URL, params={
                "query": vm_name, "start": start, "end": end, "step": step,
            }, timeout=15)
            j = r.json()
            if j.get("data") and j["data"]["result"]:
                for ts, val in j["data"]["result"][0]["values"]:
                    ts = int(float(ts))
                    timestamps.add(ts)
                    data.setdefault(ts, {})[col] = val
        except Exception:
            pass

    buf = StringIO()
    writer = csv.writer(buf)
    cols = list(ALL_METRICS.keys())
    writer.writerow(["timestamp_utc"] + cols)
    for ts in sorted(timestamps):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([dt] + [data.get(ts, {}).get(c, "") for c in cols])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wtp_data.csv"},
    )


# ── Controls ───────────────────────────────────────────────────────────────

@app.post("/valve/open")
def valve_open():
    _publish('{"cmd":"valve_open"}')
    return {"ok": True}


@app.post("/valve/close")
def valve_close():
    _publish('{"cmd":"valve_close"}')
    return {"ok": True}


@app.post("/pump/start")
def pump_start():
    _publish('{"cmd":"pump_start"}')
    return {"ok": True}


@app.post("/pump/stop")
def pump_stop():
    _publish('{"cmd":"pump_stop"}')
    return {"ok": True}


# ── Turbidity threshold ────────────────────────────────────────────────────

@app.get("/api/threshold")
def get_threshold():
    return {"value": shared_state.get_threshold()}


@app.post("/api/threshold")
async def set_threshold(request: Request):
    body = await request.json()
    try:
        shared_state.set_threshold(float(body["value"]))
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"value": shared_state.get_threshold()}


# ── Alum dose ──────────────────────────────────────────────────────────────

class DoseRequest(BaseModel):
    dose_mg_per_l: float


# ── Relay interval ─────────────────────────────────────────────────────────

class RelayConfig(BaseModel):
    on_duration_seconds: float
    off_duration_seconds: float
    enabled: bool

def _read_relay() -> dict:
    try:
        data = json.loads(RELAY_STATE_FILE.read_text())
        data.setdefault("on_duration_seconds", 5.0)
        data.setdefault("off_duration_seconds", 10.0)
        return data
    except Exception:
        return {"on_duration_seconds": 5.0, "off_duration_seconds": 10.0, "enabled": False}

def _write_relay(data: dict) -> None:
    RELAY_STATE_FILE.write_text(json.dumps(data))

@app.get("/relay/config")
def get_relay_config():
    return _read_relay()

@app.post("/relay/config")
def set_relay_config(body: RelayConfig):
    if body.on_duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="ON duration must be positive")
    if body.off_duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="OFF duration must be positive")
    data = {
        "on_duration_seconds": body.on_duration_seconds,
        "off_duration_seconds": body.off_duration_seconds,
        "enabled": body.enabled,
    }
    _write_relay(data)
    return data


@app.get("/alum/dose")
def get_dose():
    dose = _read_dose()
    return {"dose_mg_per_l": dose, "ratio_ml_per_l": round(dose / STOCK_MG_PER_ML, 4)}

@app.post("/alum/dose")
def set_dose(body: DoseRequest):
    if body.dose_mg_per_l <= 0:
        raise HTTPException(status_code=400, detail="Dose must be positive")
    _write_dose(body.dose_mg_per_l)
    return {"dose_mg_per_l": body.dose_mg_per_l, "ratio_ml_per_l": round(body.dose_mg_per_l / STOCK_MG_PER_ML, 4)}


# ── Debug ──────────────────────────────────────────────────────────────────

@app.get("/api/table")
def get_table(start: int, end: int):
    duration = end - start
    if duration <= 3600:
        step = "10s"
    elif duration <= 86400:
        step = "5m"
    else:
        step = "30m"

    data: dict[int, dict] = {}
    timestamps: set[int] = set()

    for col, vm_name in ALL_METRICS.items():
        try:
            r = requests.get(VM_RANGE_URL, params={
                "query": vm_name, "start": start, "end": end, "step": step,
            }, timeout=15)
            j = r.json()
            if j.get("data") and j["data"]["result"]:
                for ts, val in j["data"]["result"][0]["values"]:
                    ts = int(float(ts))
                    timestamps.add(ts)
                    data.setdefault(ts, {})[col] = round(float(val), 4)
        except Exception:
            pass

    cols = list(ALL_METRICS.keys())
    rows = []
    for ts in sorted(timestamps, reverse=True):   # newest first
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        rows.append([dt] + [data.get(ts, {}).get(c) for c in cols])

    return {"columns": ["timestamp_utc"] + cols, "rows": rows, "total": len(rows)}


@app.get("/api/debug/vm")
def debug_vm():
    try:
        r = requests.get("http://localhost:8428/api/v1/label/__name__/values", timeout=3)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/status")
def status():
    return {"system": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
