---
name: TLC Integration Test Suite — Project Context
description: Architecture contracts, module layout, and test decisions for the Traffic Light Controller integration test suite
type: project
---

The integration tests target the Bench Test Traffic Light Controller (TLC) defined in ARCH-TLC-001.

**Why:** The implementation does not exist yet; tests are written against architecture contracts so that once `tlc/` modules are written, the tests verify them automatically.

**Test suite location:** `C:\Users\Half-Life\Desktop\Claude\Sys_vs_SW\TrafficLight\Agentic\tests\`

**Module layout expected by tests (tlc/ package):**
- `tlc/gpio_driver.py` — PIN_RED=17, PIN_YELLOW=27, PIN_GREEN=22, PIN_CRB=18; functions: gpio_init(), gpio_cleanup(), gpio_set_leds(red,yellow,green), gpio_read_crb()
- `tlc/debounce.py` — DebounceModule class with process(raw_pressed: bool, tick_time_ms: float) -> bool
- `tlc/state_machine.py` — StateMachine class, PhaseState IntEnum (S1_GREEN=1, S2_YELLOW=2, S3_RED=3, S4_PED=4, S_ERROR=99); SM fields: current_state, cr_pending, phase_start_ms; methods: __init__(gpio), initialize(tick_time_ms), update(valid_press_event, tick_time_ms) -> PhaseState, enter_error_state()
- `tlc/timing.py` — now_ms(), elapsed_ms(start_ms), and all DURATION_* / DEBOUNCE_* constants

**How to apply:** Any future test additions must match these contracts. If the implementation deviates, update these notes.
