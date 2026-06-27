# Troubleshooting Guide

This guide is written for operators and technicians — no programming knowledge required. Work through the relevant section step by step. If a step fixes the problem, stop there.

---

## Before You Begin

**Things you need:**
- A phone or laptop connected to the same Wi-Fi as the Pi
- The dashboard address (usually `http://<pi-ip>:8000`)
- Physical access to the Pi and the control panel

**The golden rule — try a restart first:**
1. Unplug the Pi's power cable for 10 seconds, then plug it back in.
2. Wait 60 seconds for everything to start.
3. Check the dashboard. If it loads and shows numbers, you're done.

---

## Problem 1 — Dashboard Won't Load

You type the address into your browser and get an error or blank page.

**Step 1 — Check the Pi is powered on.**
Look for a solid red LED on the Pi board. If it is off or flickering, the Pi has no power. Check the power cable and power supply.

**Step 2 — Check you are on the same network.**
Your phone or laptop must be on the same Wi-Fi as the Pi. Try connecting to the local network, not mobile data.

**Step 3 — Confirm the IP address.**
If the Pi's IP address has changed (after a router restart, for example), you need to find the new one. Ask someone with system access to check, or look at your router's connected-devices list.

**Step 4 — Wait longer.**
After a power cycle the Pi needs up to 60–90 seconds before the dashboard is ready. The red LED turns on, then the green LED flickers as it boots. Wait for the green LED to settle.

**Step 5 — Check the login.**
The dashboard asks for a username and password. Default: **username `admin`, password `reno@123`**. Passwords are case-sensitive.

---

## Problem 2 — Dashboard Loads but Shows "—" for All Values

The page opens but every number shows a dash instead of a reading.

**Step 1 — Check the live dot.**
In the top-left corner of the dashboard there is a small green dot. If it is red, the browser cannot reach the Pi's data service. Restart the Pi (unplug for 10 seconds).

**Step 2 — Wait 2 minutes after startup.**
Data only appears once both sensors have been successfully polled. Give the system time to fill in.

**Step 3 — Check the USB-to-RS485 adapters.**
The flow meter and turbidity sensor each connect through a small USB adapter plugged into the Pi.
- Look at the side of the Pi — there should be **two USB adapters** plugged in.
- Each adapter usually has a small green or red LED that flickers when data is being exchanged.
- If an adapter is missing or its LED is solid (not flickering), reseat it: unplug it and plug it back in firmly.

**Step 4 — Check the RS-485 wiring at the sensors.**
Each sensor has a 2-wire RS-485 cable (labelled **A+** and **B−** or similar). Confirm:
- Both wires are firmly connected at the sensor terminal block — no loose ends.
- Both wires are firmly connected at the USB adapter terminal block on the other end.
- A wire is in **A**, B wire is in **B**. Swapped A/B causes no communication (no damage, just silence).

---

## Problem 3 — Flow Rate Shows 0 or "—" but Water is Flowing

**Step 1 — Check the USB adapter for the flow meter.**
The flow meter uses the adapter labelled `/dev/ttyUSB1` (it is usually the first one plugged in). Unplug and replug it.

**Step 2 — Inspect the RS-485 cable from the flow meter.**
Follow the cable from the flow meter to the USB adapter. Check for:
- Damaged insulation or a bent/broken wire
- A loose terminal — tug gently on each wire; it should not pull out

**Step 3 — Check the flow meter power.**
The flow meter needs its own 24V DC supply (or as specified on its label). Confirm the supply is on and the meter's display or LED is illuminated.

**Step 4 — Check the Modbus address.**
The flow meter must be set to **Modbus address 1**. This is usually a DIP switch or menu setting on the meter itself. Refer to the meter's manual to confirm the address.

---

## Problem 4 — Turbidity Shows "—" or a Wildly Wrong Number

**Step 1 — Check the second USB adapter.**
The turbidity sensor uses the second USB adapter (`/dev/ttyUSB2`). Unplug and replug it.

**Step 2 — Inspect the RS-485 wiring at the turbidity meter.**
Same checks as Problem 3, Step 2.

**Step 3 — Check the sensor is submerged / installed correctly.**
The turbidity sensor must be in the water flow path and not exposed to air. An air bubble in front of the sensor will give false high readings.

**Step 4 — Check the Modbus address.**
The turbidity meter must be set to **Modbus address 4**. Refer to its manual.

**Step 5 — Clean the sensor.**
If the turbidity reading is much higher than expected and the water looks clear, the sensor window may be fouled with scale or algae. Clean it with a soft cloth and clean water.

---

## Problem 5 — Valves S1 or S2 Not Responding

The dashboard shows S1 OPEN or CLOSED but the physical valve is not in that position.

**Step 1 — Confirm the correct valve pin.**
- **S1 (Main Valve)** is wired to **GPIO pin BCM 18** (physical board pin 12)
- **S2 (Aux/Diverter Valve)** is wired to **GPIO pin BCM 17** (physical board pin 11)

**Step 2 — Check the wiring at the GPIO header.**
The 40-pin GPIO header on the Pi is where the solenoid driver wires connect. Ensure:
- The signal wire is in the correct pin hole (count from the corner of the header)
- The ground wire is in a GND pin (there are several; any GND pin will work)
- No wires have slipped out — give each a gentle tug

**Step 3 — Check the solenoid driver / relay board.**
The GPIO pins output only 3.3V at very low current — they cannot drive a solenoid directly. There should be a relay module or transistor driver board in between. Check:
- The driver board is powered (it usually has its own power connector separate from the signal wire)
- The LED on the relay module changes state when the valve should switch — if the LED changes but the valve doesn't move, the problem is in the valve itself or its power supply

**Step 4 — Check the solenoid valve power supply.**
Solenoid valves typically run on 12V or 24V DC. Confirm the power supply to the valve is on and at the correct voltage.

**Step 5 — Check that turbidity is below the alarm threshold.**
If turbidity is above the threshold set in the dashboard, the system intentionally closes S1 and opens S2. This is normal behaviour — not a fault. Lower the threshold or resolve the turbidity issue first.

---

## Problem 6 — Relay (Pin 16) Not Clicking

The relay is the small clicking switch used for an interval-controlled pump or device. Its status is shown in the **Relay Switch — Pin 16** card on the dashboard.

**Step 1 — Confirm the relay loop is enabled.**
On the dashboard, in the Relay card, check that the **Enable loop** checkbox is ticked and that you have clicked **Save**. If it is not enabled, the relay stays off.

**Step 2 — Check the ON and OFF durations.**
Both durations must be greater than zero. If either is 0, the relay will not cycle.

**Step 3 — Check the wiring at GPIO pin BCM 16.**
Physical pin 36 on the board (count from the corner). The relay module's signal wire should be here. Same checks as Problem 5, Step 2.

**Step 4 — Check the relay module LED.**
The relay module should have a small LED that lights when the relay is energised. This module is **active-LOW** — the LED turns on when the Pi sends a LOW signal. If the LED is not changing, the wiring or the module has a fault.

**Step 5 — Verify orientation: the relay is active-LOW.**
For this system the relay energises when the GPIO pin goes LOW (not HIGH). If you wired a normally-open (NO) contact, the circuit will be open when idle and closed when the relay fires. If you wired a normally-closed (NC) contact, the opposite is true. Make sure the correct terminals on the relay output are used for your application.

---

## Problem 7 — Turbidity Alarm Keeps Triggering Falsely

The S1 valve keeps closing even though the water looks clean.

**Step 1 — Check the turbidity threshold.**
On the dashboard, find the **Turbidity** card. The threshold shows how high the turbidity (in NTU) must go before the alarm fires. If the threshold is set too low (e.g. 1 NTU) it will trigger on clean water. Increase the threshold and click **Set**.

**Step 2 — Clean the sensor.**
A dirty sensor window will read high. See Problem 4, Step 5.

**Step 3 — Check for air bubbles.**
Air in the flow path causes very high false readings. Bleed the line.

**Step 4 — Check for electrical interference.**
RS-485 wiring near large motors or variable-frequency drives can pick up interference. Ensure the signal cable is away from power cables and uses shielded cable with the shield grounded at one end.

---

## Problem 8 — No Data from RPi2 (Chemical Treatment Sensors Show "—")

The pH, ORP, temperature (RTD), EC, and pump readings all show "—".

**Step 1 — Check that RPi2 is running.**
RPi2 is a separate Raspberry Pi handling the chemical treatment side. Confirm it is powered on.

**Step 2 — Check the network connection between the two Pis.**
Both Pis must be on the same network (wired or Wi-Fi). If the Tailscale VPN is in use, ensure it is active on both.

**Step 3 — Check the Zenoh router on RPi1.**
The two Pis communicate through a Zenoh router running on RPi1. Restart RPi1 (see the golden rule at the top). The router starts automatically.

**Step 4 — Check RPi2's application is running.**
If RPi2's software has crashed, it will stop sending data. Restart RPi2.

---

## Problem 9 — Alum Dose Seems Wrong

The pump is running faster or slower than expected.

**Step 1 — Check the dose setting.**
On the dashboard, scroll to the **Alum Dosing** section. The **Target Dose (mg/L)** field shows the current setting. Adjust it and click **Save**.

**Step 2 — Understand the calculation.**
The system calculates alum pump rate as:
> **pump rate (mL/min) = flow rate (L/min) × dose (mg/L) ÷ 50**

The ÷ 50 comes from the stock solution concentration (50 mg per mL). If your stock concentration is different, the calculation will be wrong — this requires a code change.

**Step 3 — Check that the flow meter is reading correctly.**
If the flow rate is wrong (see Problem 3), the dose calculation will also be wrong.

---

## Problem 10 — Pi Keeps Restarting or Crashing

**Step 1 — Check the power supply.**
The Pi requires a stable 5V, 3A supply. Underpowered supplies cause random restarts. Use the official Pi power supply or equivalent.

**Step 2 — Check for overheating.**
The Pi will throttle and crash if it overheats. Ensure the Pi has ventilation and is not in a sealed enclosure. A heatsink is recommended.

**Step 3 — Check the SD card.**
A failing SD card causes random crashes and corrupted files. If the problem is frequent, the SD card may need replacing.

**Step 4 — Check disk space.**
VictoriaMetrics stores data indefinitely. If the SD card fills up, the Pi will malfunction. Check free space: a tech person can run `df -h` on the Pi.

---

## Quick Reference: Wiring Summary

| What | Where on Pi | Notes |
|---|---|---|
| Solenoid 1 (Main Valve) | BCM 18 — physical pin 12 | HIGH = valve open |
| Solenoid 2 (Aux Valve) | BCM 17 — physical pin 11 | HIGH = valve open |
| Relay switch | BCM 16 — physical pin 36 | LOW = relay energised |
| Flow meter RS-485 | USB adapter 1 | Modbus address 1, A+ and B− |
| Turbidity sensor RS-485 | USB adapter 2 | Modbus address 4, A+ and B− |
| Ground (all) | Any GND pin | Multiple GND pins on the header |

**GPIO header pin numbering diagram (top view, USB ports at bottom):**

```
     3V3  [ 1][ 2]  5V
   GPIO2  [ 3][ 4]  5V
   GPIO3  [ 5][ 6]  GND
   GPIO4  [ 7][ 8]  GPIO14
     GND  [ 9][10]  GPIO15
  GPIO17  [11][12]  GPIO18   ← S2 valve  ← S1 valve
  GPIO27  [13][14]  GND
  GPIO22  [15][16]  GPIO23
     3V3  [17][18]  GPIO24
  GPIO10  [19][20]  GND
   GPIO9  [21][22]  GPIO25
  GPIO11  [23][24]  GPIO8
     GND  [25][26]  GPIO7
   GPIO0  [27][28]  GPIO1
   GPIO5  [29][30]  GND
   GPIO6  [31][32]  GPIO12
  GPIO13  [33][34]  GND
  GPIO19  [35][36]  GPIO16   ← Relay
  GPIO26  [37][38]  GPIO20
     GND  [39][40]  GPIO21
```

---

## Reading the System Logs (journalctl)

When something is wrong and the steps above do not explain it, the system logs are the next place to look. Logs record everything the software does — errors, warnings, and normal activity — with timestamps.

You will need to type commands into a **terminal** on the Pi. You can do this by:
- Connecting a keyboard and monitor directly to the Pi
- Connecting over SSH: open a terminal on your laptop and type `ssh suprabha@<pi-ip-address>`

The service is named **`reno-rpi1`**. All commands below use that name.

---

### Check if the service is running

```bash
sudo systemctl status reno-rpi1
```

This is always the first command to run. It shows:
- Whether the service is **active (running)**, **inactive (dead)**, or **failed**
- The last few lines of the log
- How long it has been running

**What you'll see when everything is fine:**
```
● reno-rpi1.service - RENO RPi1 Water Treatment Controller
     Loaded: loaded (/etc/systemd/system/reno-rpi1.service; enabled)
     Active: active (running) since Fri 2026-06-27 08:00:01 +05:30; 2h 14min ago
   Main PID: 1234 (python3)
```

**What you'll see when it has crashed:**
```
● reno-rpi1.service - RENO RPi1 Water Treatment Controller
     Active: failed (Result: exit-code) since Fri 2026-06-27 10:15:33 +05:30
```

---

### Start the service (if it is stopped)

```bash
sudo systemctl start reno-rpi1
```

Then wait 30 seconds and check the dashboard.

---

### Stop the service

```bash
sudo systemctl stop reno-rpi1
```

---

### Restart the service

```bash
sudo systemctl restart reno-rpi1
```

Useful after a wiring change or config edit without rebooting the whole Pi.

---

### Enable the service to start automatically on boot

```bash
sudo systemctl enable reno-rpi1
```

If you find the service is not starting after a power cut, run this once.

---

### View the full log (all time)

```bash
sudo journalctl -u reno-rpi1
```

This shows the entire log history. It opens in a scrollable viewer:
- Press **Space** or **Page Down** to scroll forward
- Press **b** or **Page Up** to scroll back
- Press **G** (capital G) to jump to the newest entry
- Press **q** to quit

---

### View only the most recent entries

```bash
sudo journalctl -u reno-rpi1 -n 50
```

Shows the last 50 lines. Change `50` to any number you want.

---

### Watch the log live (as it happens)

```bash
sudo journalctl -u reno-rpi1 -f
```

The terminal will update in real time as new log lines appear. Press **Ctrl+C** to stop watching.

This is useful when you are making a change (e.g. plugging in a sensor) and want to see immediately whether the software notices it.

---

### View logs since the last boot only

```bash
sudo journalctl -u reno-rpi1 -b
```

Useful after a reboot — filters out logs from before the restart so you only see what happened this session.

---

### View logs from a specific time

```bash
sudo journalctl -u reno-rpi1 --since "2026-06-27 10:00:00"
```

```bash
sudo journalctl -u reno-rpi1 --since "2026-06-27 09:00:00" --until "2026-06-27 10:00:00"
```

Replace the dates and times with the window you want to investigate.

---

### Search for errors only

```bash
sudo journalctl -u reno-rpi1 -p err
```

Filters to show only error-level messages, cutting out the normal noise.

---

### Save the log to a file (to send to a developer)

```bash
sudo journalctl -u reno-rpi1 -b > ~/reno-log.txt
```

This saves everything from the current boot into a file called `reno-log.txt` in the home folder. You can then copy it to a USB drive or send it by email.

---

### What the log messages mean

#### Normal messages (nothing is wrong)

| Message | Meaning |
|---|---|
| `VictoriaMetrics running (pid …)` | Database started successfully |
| `Zenoh router running (pid …)` | Messaging router started |
| `Zenoh receiver started` | Listening for RPi2 data |
| `Web UI → http://0.0.0.0:8000` | Dashboard is ready |
| `System online — monitoring dual-valve filtration` | Sensor loop is running |
| `flow=12.50 \| turbidity=3.45 \| V1=ON V2=OFF \| alum=2.50 mL/min` | Normal sensor reading every second |
| `Relay ON for 120s` | Relay has energised |
| `Relay OFF for 600s` | Relay has de-energised |

#### Warning messages (investigate but not immediately critical)

| Message | Meaning |
|---|---|
| `Flow meter read failed: …` | Could not get a reading from the flow sensor — check USB adapter and RS-485 wiring (see Problem 3) |
| `Turbidity read failed: …` | Could not get a reading from the turbidity sensor — check USB adapter and wiring (see Problem 4) |
| `VictoriaMetrics write failed, retrying: …` | Database write failed temporarily — it will retry 3 times. If this repeats constantly, VictoriaMetrics may have crashed |
| `Could not connect to flow meter on /dev/ttyUSB1` | USB adapter not detected at startup — unplug and replug the adapter, then restart the service |
| `Could not connect to turbidity meter on /dev/ttyUSB2` | Same as above for the turbidity adapter |
| `Could not create alum Zenoh publisher: …` | The Zenoh router is not ready yet — usually self-resolves on next attempt |
| `Tailscale Funnel: …` | Public URL not available via Tailscale — dashboard is still accessible on the local network |
| `ngrok error: …` | Public tunnel not available — does not affect local operation |

#### Error messages (action required)

| Message | Meaning |
|---|---|
| `VictoriaMetrics exited immediately: …` | Database crashed at startup — check disk space (`df -h`) and that the binary path is correct |
| `Zenoh router exited immediately: …` | Zenoh router crashed — ensure `zenohd` is installed at `/usr/local/bin/zenohd` |
| `Stopping sensor loop` | The sensor loop was interrupted — check what happened just before this line |
| `ModuleNotFoundError: …` | A required Python package is missing — a developer needs to run `pip install -r requirements.txt` |
| `PermissionError: … /dev/ttyUSB…` | The Pi user does not have permission to access the USB serial port — run `sudo usermod -a -G dialout suprabha` and reboot |
| `RuntimeError: Not running on a RPi` | The software is running on a non-Pi machine that cannot control GPIO — only relevant in a development environment |

---

### Common sequence: service crashed, find out why

```bash
# Step 1 — check status and see the last few lines
sudo systemctl status reno-rpi1

# Step 2 — look at logs since the last boot for more detail
sudo journalctl -u reno-rpi1 -b

# Step 3 — press G to jump to the end and look for ERROR or WARNING lines

# Step 4 — restart and watch live to see if it recovers
sudo systemctl restart reno-rpi1
sudo journalctl -u reno-rpi1 -f
```

---

## When to Call for Technical Help

Contact a technician or developer if:
- You have restarted the Pi and the dashboard still does not load after 5 minutes
- A sensor or valve was working, stopped, and none of the steps above resolved it
- There is visible physical damage to wiring, connectors, or the Pi board
- The SD card or operating system appears to be corrupted (dashboard loads but shows errors about files)
- You need to change a Modbus device address, serial port assignment, or GPIO pin
