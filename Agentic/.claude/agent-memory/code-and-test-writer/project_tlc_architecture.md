---
name: TLC project architecture
description: Traffic Light Controller (TLC) for Raspberry Pi — module layout, key semantics, and the one non-obvious fix discovered during implementation
type: project
---

Project path: `C:\Users\Half-Life\Desktop\Claude\Sys_vs_SW\TrafficLight\Agentic`

Module layout:
- `tlc/timing.py` — constants (TICK_PERIOD, phase durations, debounce thresholds); do not modify
- `tlc/gpio_driver.py` — real RPi.GPIO wrapper; BCM pins: RED=17, YELLOW=27, GREEN=22, CRB=18 (active-low)
- `tlc/debounce.py` — DebounceModule; 50 ms stability window + 300 ms lockout; emits on HELD path AND release path
- `tlc/state_machine.py` — StateMachine; phases S1_GREEN→S2_YELLOW→S3_RED→(S4_PED|S1_GREEN)→S1_GREEN
- `tlc/main.py` — entry point; 10 ms tick loop
- `tests/test_helpers.py` — stubs RPi.GPIO via sys.modules before any tlc import; defines MockGPIODriver

RPi.GPIO stub: `sys.modules.setdefault("RPi", ...)` in test_helpers.py — import is safe on Windows.

Key non-obvious semantic (discovered via test failure):
- `cr_pending` must be cleared when S3_RED transitions TO S4_PED (at the RED→PED boundary), NOT when S4_PED exits to S1_GREEN.
- Tests assert `sm.cr_pending == False` at the very first tick inside S4_PED, so the clear must happen during the transition step that sets next_state = S4_PED.

**Why:** FR-010 text says "cleared after walk" but the tests implement "cleared on entry to walk". The test comment says "CR was cleared when we entered S4_PED from RED."

**How to apply:** In the S3_RED branch, set `self.cr_pending = False` before setting `next_state = PhaseState.S4_PED`.
