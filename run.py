import threading
import uvicorn
from full_system_package import start

def run_ui():
    uvicorn.run(
        "water_ui.ui.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
    )

if __name__ == "__main__":
    ui_thread = threading.Thread(target=run_ui, daemon=True)
    ui_thread.start()
    print("Web UI started at http://0.0.0.0:8000")
    start()
