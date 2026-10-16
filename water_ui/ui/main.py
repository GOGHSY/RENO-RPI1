import json
import os
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import zenoh

app = FastAPI()

# Directory Setup
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Alum dose state file — shared with the main sensor loop
DOSE_STATE_FILE = Path(__file__).resolve().parents[2] / "dose_state.json"
STOCK_CONCENTRATION_MG_PER_ML = 50.0  # 50,000 mg/L = 50 mg/mL

def _read_dose() -> float:
    try:
        return json.loads(DOSE_STATE_FILE.read_text())["dose_mg_per_l"]
    except Exception:
        return 10.0  # default 10 mg/L

def _write_dose(dose: float) -> None:
    DOSE_STATE_FILE.write_text(json.dumps({"dose_mg_per_l": dose}))

# VictoriaMetrics endpoint
VM_URL = "http://localhost:8428/api/v1/query"

# Zenoh — initialized lazily so the web server starts even if Zenoh is unavailable
_zenoh_session = None
_zenoh_pub = None

def _get_publisher():
    global _zenoh_session, _zenoh_pub
    if _zenoh_pub is not None:
        return _zenoh_pub
    try:
        _zenoh_session = zenoh.open(zenoh.Config())
        _zenoh_pub = _zenoh_session.declare_publisher("water/control")
    except Exception as e:
        print(f"Zenoh unavailable: {e}")
        _zenoh_pub = None
    return _zenoh_pub


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/metrics/{metric_key}")
def get_vm_metric(metric_key: str):
    """Bridge for the frontend to fetch VictoriaMetrics data"""
    metrics_map = {
        "flow": "filtration_flow_rate",
        "flocPh": "water_treatment_pH2",  # RPI2 pH2 = Post Floc
        "ntu": "filtration_turbidity",
        "effPh": "water_treatment_pH3",   # RPI2 pH3 = Post Sed, last pH probe
        "ec": "water_treatment_EC",
    }

    query = metrics_map.get(metric_key)
    if not query:
        return {"value": 0.0, "error": "Invalid key"}

    try:
        # Use synchronous requests since we aren't using httpx
        response = requests.get(VM_URL, params={"query": query}, timeout=2)
        res_json = response.json()

        if res_json.get("data") and res_json["data"]["result"]:
            # VictoriaMetrics returns [timestamp, "value"]
            val = res_json["data"]["result"][0]["value"][1]
            return {"value": float(val)}
        return {"value": 0.0}
    except Exception as e:
        return {"value": 0.0, "error": str(e)}


# Zenoh POST Endpoints
@app.post("/valve/open")
def valve_open():
    pub = _get_publisher()
    if pub is None:
        raise HTTPException(status_code=503, detail="Zenoh unavailable")
    pub.put('{"cmd":"valve_open"}')
    return {"ok": True}


@app.post("/valve/close")
def valve_close():
    pub = _get_publisher()
    if pub is None:
        raise HTTPException(status_code=503, detail="Zenoh unavailable")
    pub.put('{"cmd":"valve_close"}')
    return {"ok": True}


@app.post("/pump/start")
def pump_start():
    pub = _get_publisher()
    if pub is None:
        raise HTTPException(status_code=503, detail="Zenoh unavailable")
    pub.put('{"cmd":"pump_start"}')
    return {"ok": True}


@app.post("/pump/stop")
def pump_stop():
    pub = _get_publisher()
    if pub is None:
        raise HTTPException(status_code=503, detail="Zenoh unavailable")
    pub.put('{"cmd":"pump_stop"}')
    return {"ok": True}


class DoseRequest(BaseModel):
    dose_mg_per_l: float

@app.get("/alum/dose")
def get_dose():
    dose = _read_dose()
    ratio = dose / STOCK_CONCENTRATION_MG_PER_ML
    return {"dose_mg_per_l": dose, "ratio_ml_per_l": round(ratio, 4)}

@app.post("/alum/dose")
def set_dose(body: DoseRequest):
    if body.dose_mg_per_l <= 0:
        raise HTTPException(status_code=400, detail="Dose must be positive")
    _write_dose(body.dose_mg_per_l)
    ratio = body.dose_mg_per_l / STOCK_CONCENTRATION_MG_PER_ML
    return {"dose_mg_per_l": body.dose_mg_per_l, "ratio_ml_per_l": round(ratio, 4)}


@app.get("/status")
def status():
    return {"system": "running", "valve": "unknown", "pump": "unknown"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
