# TODO — Technical Debt & Improvement Opportunities


## Potential Bugs

- **`receiver.py` uses `print()` instead of `logging`** — `listener()` and `start_receiver()` use `print()` directly, bypassing the configured logging system. These logs will not appear with timestamp/level prefixes.
- **Default credential warning never fires** — `water_ui/ui/main.py` line 46 checks `if BASIC_USER == "admin" and BASIC_PASS == "sem129wtp"` but the actual default password is `"reno@123"`, so the warning condition is never true.
- **`TurbiditySensor.read_voltage()` naming** — The method name implies a voltage reading but actually returns NTU (Nephelometric Turbidity Units). This is misleading. Rename to `read_ntu()`.
- **`relay_state.json` path is ambiguous between run.py and water_ui** — `RELAY_STATE_FILE` is resolved relative to the file doing the resolution (`parents[1]` vs `parents[2]`). If the process working directory changes, these could diverge. Using an absolute path relative to the project root (as `shared_state.py` does with `Path(__file__).resolve().parent`) would be safer.
- **No atomic file writes** — `Path.write_text()` is not atomic. If the process crashes mid-write, the JSON file could be corrupted. Using `tempfile` + `os.rename()` would be safer.
- **Zenoh alum publisher silently drops messages on session failure** — `_get_alum_publisher()` returns `None` on exception, and `start()` checks `if pub:` before publishing. This is safe but silent; a WARNING log would help diagnose connectivity issues.

---

## Missing Configuration

- **Hardcoded RPi2 IP address** — `services/receiver.py` has `ZENOH_ROUTER = "tcp/100.96.169.94:7447"` hardcoded. This should be an environment variable or a config file entry to support different deployments.
- **Hardcoded binary paths** — `run.py` has `VICTORIA_METRICS_BIN` and `ZENOHD_BIN` hardcoded. These should be configurable, ideally from a `.env` file (the `python-dotenv` package is already in `requirements.txt` but unused).
- **VictoriaMetrics data retention** — No `-retentionPeriod` flag is set. Storage will grow indefinitely.

---

## Security

- **Default credentials in source** — `BASIC_PASS = "reno@123"` is committed to git. This is acceptable for a local IoT device but should be documented and changed before any internet exposure.
- **InfluxDB token hardcoded in `config.py`** — Even though InfluxDB is no longer used, the token is still visible in the source code. Rotate and remove.
- **No HTTPS** — The dashboard is served over plain HTTP. When exposed via Tailscale or ngrok, this is partially mitigated, but the Pi-local traffic is unencrypted.

---

## Technical Debt

- **No automated tests** — The entire codebase has zero unit or integration tests. Key units to test: `ControlManager.should_shutdown()`, `VictoriaMetricsLogger` line formatting, `shared_state` concurrency, API endpoints.
- **No `pyproject.toml` or `setup.py`** — The project has no package definition. Dependencies are listed only in `requirements.txt` without version pins, risking breakage on re-install. Pin versions or switch to `pyproject.toml` with `[project.dependencies]`.
- **Relay countdown in UI is client-side only** — The relay countdown timer in `index.html` is a JavaScript estimate that starts fresh on page load. It drifts from the actual hardware state. The `/api/live` endpoint could expose remaining phase time to allow accurate display.
- **CSV download fetches all metrics serially** — `download_csv()` makes one HTTP request to VictoriaMetrics per metric (15 requests). These could be parallelised with `asyncio` or `concurrent.futures` for faster exports.

---

## Suggested Improvements

1. **Move all hardcoded values to environment variables** — Use `python-dotenv` (already in requirements) to load a `.env` file for: RPi2 IP, binary paths, credentials, Modbus ports.
2. **Add a `systemd` unit file** — Document (or provide) a `reno-rpi1.service` file for production deployment.
3. **Add a health endpoint that checks subsystems** — Current `/status` just returns `{"system": "running"}`. A real health check would verify VictoriaMetrics reachability, Zenoh session status, and Modbus connection state.
4. **Server-Sent Events or WebSocket for live data** — Polling every 2 seconds is simple but inefficient. SSE would push updates only when data changes.
5. **Logging to file** — Configure a rotating file handler so logs persist across restarts for post-incident review.
6. **Rename `read_voltage()` to `read_ntu()`** in `TurbiditySensor` — reduces confusion.
7. **Consider a `conftest.py` with hardware mocks** to enable unit testing without a Pi.
