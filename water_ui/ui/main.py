import os
from contextlib import asynccontextmanager
from pathlib import Path

import requests
import zenoh
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

VM_URL = "http://localhost:8428/api/v1/query"

ZENOH_KEY = "water/control"

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


def _publish(cmd: str):
    if _zenoh_pub is None:
        raise HTTPException(status_code=503, detail="Zenoh not connected")
    _zenoh_pub.put(cmd.encode())


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/metrics/{metric_key}")
def get_vm_metric(metric_key: str):
    metrics_map = {
        "flow": "intake_flow_rate",
        "flocPh": "floc_ph_level",
        "ntu": "filtration_turbidity",
        "effPh": "effluent_ph_level",
        "ec": "effluent_conductivity",
    }

    query = metrics_map.get(metric_key)
    if not query:
        return {"value": 0.0, "error": "Invalid key"}

    try:
        response = requests.get(VM_URL, params={"query": query}, timeout=2)
        res_json = response.json()
        if res_json.get("data") and res_json["data"]["result"]:
            val = res_json["data"]["result"][0]["value"][1]
            return {"value": float(val)}
        return {"value": 0.0}
    except Exception as e:
        return {"value": 0.0, "error": str(e)}


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


@app.get("/status")
def status():
    return {"system": "running", "valve": "unknown", "pump": "unknown"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
