# Quick-Start Guide: Bench Test Traffic Light Controller

**Document reference:** SYS-TLC-001 / ARCH-TLC-001  
**Audience:** Lab operators and developers setting up the bench prototype for the first time  
**Time to complete:** Under 5 minutes

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Hardware Wiring](#2-hardware-wiring)
3. [Get the Code](#3-get-the-code)
4. [Run the Controller](#4-run-the-controller)
5. [Run the Tests](#5-run-the-tests)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites

| Requirement | Detail |
|-------------|--------|
| Raspberry Pi | Any model with a 40-pin GPIO header (3B, 3B+, 4B, 5, Zero 2W, or later) |
| Operating system | Raspberry Pi OS, Bullseye (64-bit) or later |
| Python | Python 3 (pre-installed on Raspberry Pi OS) |
| GPIO library | RPi.GPIO — install with `pip3 install RPi.GPIO` if not present |
| Hardware | 3x LEDs (red, yellow, green), 3x 270 Ω resistors, 1x momentary pushbutton, breadboard, jumper wires |

> **Note:** 330 Ω resistors are an acceptable substitute for 270 Ω. Do not use resistors below 220 Ω.

---

## 2. Hardware Wiring

Wire each component between the listed GPIO pin and GND as shown below. All GPIO numbers use BCM (Broadcom) numbering.

| Component | Pi GPIO (BCM) | 40-pin Header Pin | To | Notes |
|-----------|--------------|-------------------|----|-------|
| Red LED + 270 Ω resistor | GPIO 17 | Pin 11 | GND (Pin 6) | Anode → GPIO 17; cathode → GND through resistor |
| Yellow LED + 270 Ω resistor | GPIO 27 | Pin 13 | GND (Pin 6) | Anode → GPIO 27; cathode → GND through resistor |
| Green LED + 270 Ω resistor | GPIO 22 | Pin 15 | GND (Pin 6) | Anode → GPIO 22; cathode → GND through resistor |
| CRB momentary button | GPIO 18 | Pin 12 | GND (Pin 6) | No external resistor needed — internal pull-up enabled in software |

**LED circuit (per LED):**

```
GPIO pin ──── [270 Ω] ──── LED anode ──── LED cathode ──── GND
```

**Button circuit:**

```
GPIO 18 (Pin 12) ──── button terminal A
                      button terminal B ──── GND (Pin 6)
```

The button uses the Raspberry Pi's internal ~50 kΩ pull-up resistor. When the button is open, GPIO 18 reads HIGH (released). When pressed, it reads LOW (active-low logic). A disconnected wire is safe — it reads as released, not pressed.

---

## 3. Get the Code

**Option A — clone via git:**

```bash
git clone <your-repo-url> ~/Desktop/TrafficLight
```

**Option B — copy via scp from a development machine:**

```bash
scp -r ./Agentic pi@raspberrypi.local:~/Desktop/TrafficLight/
```

After either option, verify the directory structure looks like this:

```
~/Desktop/TrafficLight/Agentic/
├── tlc/
│   ├── main.py
│   ├── state_machine.py
│   ├── debounce.py
│   ├── gpio_driver.py
│   └── timing.py
└── tests/
    └── test_*.py
```

---

## 4. Run the Controller

> **Important:** You must run the controller from the `Agentic/` directory, not from inside `tlc/`. Running from `tlc/` will cause a `ModuleNotFoundError`.

```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m tlc.main
```

**Expected behavior on startup:**

1. All LEDs are off briefly (< 500 ms).
2. The green LED illuminates — the GREEN phase begins.
3. The controller cycles automatically: GREEN (7 s) → YELLOW (3 s) → RED (7 s) → repeat.
4. Press the crosswalk button during any phase. A PEDESTRIAN WALK phase (red LED, 10 s) will be inserted after the current RED phase completes.

**Stop the controller:**

Press `Ctrl+C`. GPIO cleanup runs automatically in the `finally` block — all LEDs will turn off cleanly.

---

## 5. Run the Tests

The test suite mocks RPi.GPIO and runs on any operating system — no Raspberry Pi hardware is required.

```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m pytest tests/ -v
```

All 108 tests should pass. The `-v` flag prints each test name and result. To run a specific requirement's tests only, name the file:

```bash
python3 -m pytest tests/test_FR018_FR020_debounce.py -v
```

---

## 6. Troubleshooting

### `ModuleNotFoundError: No module named 'tlc'`

You are running from inside the `tlc/` directory instead of from `Agentic/`. Move up one level:

```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m tlc.main
```

---

### SSH host key warning when connecting to the Pi

```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
```

The Pi's host key has changed (common after a fresh OS flash). Remove the stale key and reconnect:

```bash
ssh-keygen -R raspberrypi.local
ssh pi@raspberrypi.local
```

---

### GPIO permission error

```
RuntimeError: No access to /dev/mem.  Try running as root!
```

GPIO access requires elevated permissions. Run the controller with `sudo`:

```bash
sudo python3 -m tlc.main
```

If you prefer not to use `sudo` each time, add your user to the `gpio` group:

```bash
sudo usermod -aG gpio $USER
```

Log out and back in for the group change to take effect.

---

### All LEDs stay off after startup

Verify wiring polarity. LED anodes connect to the GPIO pins; cathodes connect to GND through the series resistor. Reversing anode and cathode is the most common bench wiring mistake.

---

### Red LED stays on and the controller stops cycling

The controller has entered the fault state (C-004). This means an undefined internal state was detected. Power-cycle the Pi to recover — the system always restarts in the GREEN phase with no pending crosswalk request.
