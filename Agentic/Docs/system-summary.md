# System Summary: Bench Test Traffic Light Controller

**Document reference:** SYS-TLC-001 / ARCH-TLC-001  
**Audience:** New team members and engineers seeking a complete project overview  
**Purpose:** Understand what the system is, how it behaves, how it was developed, and how the software is structured

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Behavior](#2-system-behavior)
3. [Development Process (V-Model)](#3-development-process-v-model)
4. [Software Architecture](#4-software-architecture)
5. [Key Design Decisions](#5-key-design-decisions)
6. [Requirement Traceability](#6-requirement-traceability)
7. [File Structure](#7-file-structure)

---

## 1. Executive Summary

The Bench Test Traffic Light Controller (TLC) is a single-intersection, single-lane traffic signal prototype implemented in Python on a Raspberry Pi. Three LEDs (red, yellow, green) represent the vehicle signal; one momentary pushbutton serves as the Crosswalk Request Button (CRB). The system continuously cycles through traffic phases and inserts a pedestrian walk interval whenever the button is pressed, honoring the request at the next safe opportunity after the RED phase completes.

The project exists as both a hardware demonstration and a learning platform for V-model embedded software development. It is assembled on a breadboard and observable with nothing more than a stopwatch, making all specified behaviors directly verifiable by a lab operator at the bench.

Every artifact in the project — specification, architecture, tests, and implementation — was produced in strict V-model order with full requirement traceability. Requirement identifiers (FR-001 through FR-020, NF-001 through NF-010, and C-001 through C-005) appear as inline code comments at the exact source lines that satisfy them, enabling direct traceability from specification clause to executable code.

---

## 2. System Behavior

### 4-Phase Finite State Machine

The controller operates as a deterministic four-state FSM. In the absence of a crosswalk request, it loops continuously through three phases. When a request is pending, a fourth phase is inserted between RED and the subsequent GREEN.

```
GREEN (7 s) --> YELLOW (3 s) --> RED (7 s) --> GREEN (repeat)
                                     |
                                 [if CR pending]
                                     |
                                     v
                            PEDESTRIAN WALK (10 s) --> GREEN
```

### Phase Timing Table

| Phase | State ID | Duration (nominal) | Tolerance | GPIO Active | LED |
|-------|----------|--------------------|-----------|-------------|-----|
| GREEN | S1_GREEN | 7000 ms | 5000–10000 ms | GPIO 22 HIGH | Green |
| YELLOW | S2_YELLOW | 3000 ms | ±100 ms | GPIO 27 HIGH | Yellow |
| RED | S3_RED | 7000 ms | 5000–10000 ms | GPIO 17 HIGH | Red |
| PEDESTRIAN WALK | S4_PED | 10000 ms | ±200 ms | GPIO 17 HIGH | Red |

> **Note:** PEDESTRIAN WALK uses the red indicator. There is no separate pedestrian LED in this prototype (see SYS-TLC-001 §3.2).

### Crosswalk Request Button (CRB)

- The CRB is monitored every tick (every 10 ms), including during phase transitions.
- A valid press (held stable for ≥ 50 ms) sets a `cr_pending` flag in the state machine.
- The flag is latched and carried forward unchanged through GREEN and YELLOW phases.
- At the end of RED, if `cr_pending` is True, the system transitions to PEDESTRIAN WALK instead of GREEN. The flag is cleared on that transition.
- Presses during PEDESTRIAN WALK are ignored entirely — `cr_pending` is not set and the walk duration is not extended (FR-012).
- Multiple presses before service result in exactly one PEDESTRIAN WALK insertion (FR-013).

### Exactly One LED at All Times

FR-005 requires that exactly one LED is illuminated during every steady-state moment. The `_LED_OUTPUTS_PER_STATE` table in `state_machine.py` enforces this: each state maps to a single `(red, yellow, green)` tuple with exactly one `True` value. GPIO writes only occur on state transitions, not on every tick.

---

## 3. Development Process (V-Model)

The project follows the V-model: left-side artifacts (specification → architecture → tests) were completed and reviewed before right-side artifacts (implementation) were written. The five stages are:

**1. System Specification (SYS-TLC-001)**

The specification defines all observable behavior without prescribing implementation. It contains:
- 20 Functional Requirements (FR-001 through FR-020)
- 10 Non-Functional Requirements (NF-001 through NF-010)
- 5 Constraints (C-001 through C-005)
- 5 Assumptions and 5 Open Questions resolved in the architecture stage

**2. Architecture (ARCH-TLC-001)**

The architecture translates every requirement into concrete implementation decisions:
- Module decomposition into five Python files with explicit responsibility boundaries
- Formal state transition table covering all 8 transitions including the CR fork at S3_RED
- Two-stage debounce algorithm: 50 ms stability window followed by 300 ms post-press lockout
- GPIO integration contracts (IC-001 through IC-005) specifying producer/consumer behavior and failure modes
- Hardware wiring specification: GPIO pin assignments, 270 Ω series resistors, active-low button with internal pull-up
- 13 test cases (TC-001 through TC-013) defined before implementation began

**3. Integration and Unit Tests**

108 tests were written in full before a single line of `tlc/` implementation code existed. All tests mock RPi.GPIO via `sys.modules` injection, allowing the complete suite to run on any OS without hardware. Tests are organized by requirement ID:

| Test file | Requirements covered |
|-----------|---------------------|
| `test_FR001_FR005_normal_cycle.py` | FR-001–FR-005: basic cycling and LED exclusivity |
| `test_FR007_FR008_FR014_cr_during_green.py` | FR-007, FR-008, FR-014: CR latched in GREEN, serviced after RED |
| `test_FR011_cr_during_red.py` | FR-011: CR pressed during RED; full RED duration honored |
| `test_FR012_cr_during_ped_ignored.py` | FR-012: press during PEDESTRIAN WALK has no effect |
| `test_FR013_multiple_presses.py` | FR-013: multiple presses yield exactly one walk insertion |
| `test_FR015_cr_during_yellow.py` | FR-015: CR latched during YELLOW, serviced after RED |
| `test_FR016_FR017_startup.py` | FR-016, FR-017: power-on enters GREEN; dark window < 500 ms |
| `test_FR018_FR020_debounce.py` | FR-018–FR-020: bounce rejection, lockout behavior |
| `test_NF001_NF004_phase_timing.py` | NF-001–NF-004: phase durations within tolerance |
| `test_NF005_transition_latency.py` | NF-005: transition latency ≤ 50 ms |
| `test_NF006_debounce_latency.py` | NF-006: debounce adds ≤ 100 ms latency |
| `test_NF007_power_recovery.py` | NF-007: restart clears all state |
| `test_C004_undefined_state.py` | C-004: undefined state triggers red-only halt |

**4. Implementation**

The `tlc/` package was written to make all 108 tests pass. No behavior was invented during implementation — every branch and condition traces to a requirement ID annotated in an inline comment. The implementation matches the architecture specification precisely: the class names, function signatures, algorithm steps, and constant names used in ARCH-TLC-001 are all present verbatim in the source files.

**5. Feedback Loop**

One discrepancy was identified during implementation: FR-010 in the original specification stated that `cr_pending` should be cleared when the PEDESTRIAN WALK phase *exits* (transitions to GREEN). The architecture and implementation instead clear `cr_pending` on *entry* to PEDESTRIAN WALK (the S3_RED → S4_PED transition). This was determined to be functionally equivalent — `cr_pending` is False throughout the entire PEDESTRIAN WALK phase in both interpretations — but the specification and architecture were updated to make the clearing point unambiguous.

---

## 4. Software Architecture

The software is a single-threaded Python 3 application structured as the `tlc` package. Five modules have strictly separated responsibilities.

### Module Summary

| Module | File | Key Responsibility | Requirements Satisfied |
|--------|------|--------------------|----------------------|
| Timing | `tlc/timing.py` | Monotonic clock (`time.monotonic()`), all phase and debounce duration constants | NF-001–004, NF-005, NF-008 |
| GPIO Driver | `tlc/gpio_driver.py` | RPi.GPIO abstraction; pin init, LED write (`gpio_set_leds`), CRB read (`gpio_read_crb`) | FR-002–005, FR-009, FR-017 |
| Debounce | `tlc/debounce.py` | `DebounceModule`: 50 ms stability window + 300 ms post-press lockout | FR-018–020, NF-006 |
| State Machine | `tlc/state_machine.py` | `StateMachine` FSM, `cr_pending` flag, GPIO output dispatch, error handler | FR-001, FR-007–016, C-004 |
| Main | `tlc/main.py` | Startup sequence, 10 ms polling loop, `RuntimeError` fault handler, GPIO cleanup | FR-001, FR-006, FR-016–017, NF-005, NF-007 |

### Main Loop Structure

The main loop executes every 10 ms (one tick). Within each tick, the following steps run in a fixed order:

```
tick_start_ms = now_ms()

1. gpio_read_crb()              -- sample raw button state (FR-006)
2. debounce.process()           -- filter bounce; emit valid_press once per press
3. state_machine.update()       -- evaluate CR, check phase timer, transition if due
4. sleep(remaining tick time)   -- pad tick to 10 ms
```

GPIO writes happen inside `state_machine.update()` only when a transition occurs, not on every tick.

### Debounce Algorithm

`DebounceModule.process()` is a two-stage filter:

- **Stage 0 — Lockout gate:** If a 300 ms lockout is active, all input is discarded and `False` is returned. When the lockout expires, the stability timer resets so the next press is evaluated cleanly.
- **Stage 1 — Stability detection:** A rising edge (released → pressed) starts a 50 ms stability timer. If the button remains pressed for 50 ms, one `True` is emitted (held-path event). If the button is released after 50 ms, one `True` is emitted on that tick (release-path event). If released before 50 ms, the timer is cancelled and no event is emitted (bounce rejection, FR-019).

Latency from physical press to event: 50–60 ms (well within the 100 ms budget of NF-006).

### State Transition Table

| Current State | Condition | Next State | Action |
|---------------|-----------|------------|--------|
| S1_GREEN | elapsed ≥ 7000 ms | S2_YELLOW | Apply YELLOW GPIO; reset phase timer |
| S2_YELLOW | elapsed ≥ 3000 ms | S3_RED | Apply RED GPIO; reset phase timer |
| S3_RED | elapsed ≥ 7000 ms AND `cr_pending` = False | S1_GREEN | Apply GREEN GPIO; reset phase timer |
| S3_RED | elapsed ≥ 7000 ms AND `cr_pending` = True | S4_PED | Clear `cr_pending`; GPIO unchanged (red stays on); reset phase timer |
| S4_PED | elapsed ≥ 10000 ms | S1_GREEN | Apply GREEN GPIO; reset phase timer |
| Any (≠ S4_PED) | valid press AND `cr_pending` = False | (same) | Set `cr_pending` = True |
| Any (≠ S4_PED) | valid press AND `cr_pending` = True | (same) | Discard (FR-013) |
| S4_PED | valid press | (same) | Discard (FR-012) |
| Unknown value | any | S_ERROR | Red only; raise `RuntimeError`; halt (C-004) |

---

## 5. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single-threaded 10 ms polling loop | Worst-case transition latency is < 18 ms (10 ms tick + < 3 ms write + ≤ 5 ms Linux jitter), providing a 32 ms margin under the 50 ms NF-005 limit. Eliminates thread-safety complexity and GIL concerns. |
| `time.monotonic()` for all timing | Immune to NTP synchronizations and DST adjustments. Drift over 8 hours is < 8 ms cumulative — imperceptible against the 100 ms YELLOW tolerance. Satisfies NF-008 with no extra mechanism. |
| Active-low CRB with internal pull-up | Fail-safe: a disconnected or broken button wire reads HIGH (released), which cannot trigger spurious crosswalk requests. Eliminates one external pull-down resistor from the bench assembly. |
| `cr_pending` cleared on S3_RED → S4_PED entry | Ensures `cr_pending` = False for the entire PEDESTRIAN WALK phase. Functionally equivalent to clearing on S4_PED exit; the clearing point is made explicit in ARCH-TLC-001 §8.5.4. |
| RPi.GPIO mocked via `sys.modules` injection | The entire 108-test suite runs on any OS without hardware. Tests import `tlc` modules after injecting a `MockGPIODriver`, so `gpio_driver.py` never calls a real GPIO library during testing. |
| GPIO writes on transitions only, not every tick | Avoids redundant hardware writes that could produce observable glitches. Satisfies NF-010 (no ambiguous indicator states). |
| `PhaseState` as `IntEnum` | Allows direct integer comparison in tests and fault injection. The `S_ERROR = 99` sentinel is outside the valid phase range, making undefined-state detection unambiguous. |

---

## 6. Requirement Traceability

Every FR, NF, and constraint identifier from SYS-TLC-001 is annotated as an inline code comment at the line in `tlc/` source where the requirement is satisfied. This provides direct traceability from source line to specification clause without requiring a separate traceability matrix to be maintained.

**Examples from the source:**

```python
# tlc/timing.py
DURATION_YELLOW_MS = 3000  # NF-002: YELLOW phase 3 s ± 100 ms
DEBOUNCE_STABLE_MS = 50    # FR-019: reject CRB transitions stable < 50 ms

# tlc/state_machine.py
self.current_state: PhaseState = PhaseState.S1_GREEN  # FR-016: power-on state
self.cr_pending = False                               # FR-016: no phantom CR at startup

# tlc/state_machine.py — S3_RED transition
if self.cr_pending:
    self.cr_pending = False        # FR-010: clear CR on entry to PED walk
    next_state = PhaseState.S4_PED # FR-008, FR-011: CR honoured
```

The test files mirror this convention — each file is named for the requirement IDs it covers (e.g., `test_FR018_FR020_debounce.py`), and individual test function names include the requirement ID being exercised.

---

## 7. File Structure

```
Agentic/
├── tlc/                              # Production source package
│   ├── __init__.py
│   ├── timing.py                     # NF-001–004, NF-005, NF-008: constants + clock
│   ├── gpio_driver.py                # FR-002–005, FR-009, FR-017: GPIO abstraction
│   ├── debounce.py                   # FR-018–020, NF-006: debounce algorithm
│   ├── state_machine.py              # FR-001, FR-007–016, C-004: FSM
│   └── main.py                       # FR-001, FR-006, FR-016–017, NF-005, NF-007
│
├── tests/                            # 108 tests — runs without hardware
│   ├── __init__.py
│   ├── test_helpers.py               # MockGPIODriver; sys.modules GPIO stub
│   ├── test_FR001_FR005_normal_cycle.py
│   ├── test_FR007_FR008_FR014_cr_during_green.py
│   ├── test_FR011_cr_during_red.py
│   ├── test_FR012_cr_during_ped_ignored.py
│   ├── test_FR013_multiple_presses.py
│   ├── test_FR015_cr_during_yellow.py
│   ├── test_FR016_FR017_startup.py
│   ├── test_FR018_FR020_debounce.py
│   ├── test_NF001_NF004_phase_timing.py
│   ├── test_NF005_transition_latency.py
│   ├── test_NF006_debounce_latency.py
│   ├── test_NF007_power_recovery.py
│   ├── test_C004_undefined_state.py
│   └── run_all_tests.py
│
└── Docs/                             # Project documentation
    ├── system-specification.md       # SYS-TLC-001: 20 FRs, 10 NFRs, 5 constraints
    ├── system-architecture.md        # ARCH-TLC-001: modules, contracts, test cases, ADRs
    ├── quick-start-guide.md          # Wiring, run, test — under 5 minutes
    └── system-summary.md             # This file
```

**Run the controller:**

```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m tlc.main
```

**Run the full test suite (any OS):**

```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m pytest tests/ -v
```
