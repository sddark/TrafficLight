---
name: Traffic Light Controller Project Context
description: Bench-test TLC project — spec doc ID, architecture doc ID, GPIO pin assignments, key design decisions
type: project
---

Project: Bench Test Traffic Light Controller (TLC) on Raspberry Pi.

**Why:** Learning/demonstration platform for hardware-software co-design workflow.

**Key documents:**
- System Specification: `Docs/system-specification.md` — Document ID SYS-TLC-001 v1.0
- Architecture Specification: `Docs/system-architecture.md` — Document ID ARCH-TLC-001 v1.0

**GPIO assignments (BCM numbering):**
- GPIO 17 (Pin 11): Red LED output
- GPIO 27 (Pin 13): Yellow LED output
- GPIO 22 (Pin 15): Green LED output
- GPIO 18 (Pin 12): CRB input, active-low, internal pull-up enabled

**Key design decisions made in ARCH-TLC-001:**
- Python 3 + RPi.GPIO library (ADR-001)
- CRB: active-low, internal pull-up (ADR-002)
- Timing: monotonic elapsed-time polling, 10 ms tick (ADR-003)
- LED series resistor: 270 Ω (330 Ω acceptable alternate) (ADR-004)
- No operator reset button (ADR-005)
- CR during PEDESTRIAN WALK: discarded per FR-012 (ADR-006)

**Software module layout:** `main.py`, `gpio_driver.py`, `debounce.py`, `state_machine.py`, `timing.py`

**How to apply:** When continuing work on this project, reference these pin assignments and module names directly. The architecture document is the single source of truth for implementation.
