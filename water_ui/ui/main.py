import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import zenoh

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

config = zenoh.Config()
config.insert_json5("connect/endpoints", '["tcp/127.0.0.1:7447"]')
z = zenoh.open(config)
pub = z.declare_publisher("water/control")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/valve/open")
def valve_open():
    pub.put('{"cmd":"valve_open"}')
    return {"ok": True}

@app.post("/valve/close")
def valve_close():
    pub.put('{"cmd":"valve_close"}')
    return {"ok": True}

@app.post("/pump/start")
def pump_start():
    pub.put('{"cmd":"pump_start"}')
    return {"ok": True}

@app.post("/pump/stop")
def pump_stop():
    pub.put('{"cmd":"pump_stop"}')
    return {"ok": True}

@app.get("/status")
def status():
    return {"system": "running", "valve": "unknown", "pump": "unknown"}
