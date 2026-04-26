# Architecture Specification: Bench Test Traffic Light Controller

**Document ID:** ARCH-TLC-001
**Version:** 1.0
**Date:** 2026-04-26
**Status:** Released for Implementation
**References:** SYS-TLC-001 v1.0 (System Specification, Bench Test Traffic Light Controller)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope and System Boundary](#2-scope-and-system-boundary)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Assumption and Open Question Resolution](#5-assumption-and-open-question-resolution)
6. [System Architecture Overview](#6-system-architecture-overview)
7. [Hardware Specifications](#7-hardware-specifications)
8. [Software Architecture](#8-software-architecture)
9. [Integration Contracts](#9-integration-contracts)
10. [Test Specification](#10-test-specification)
11. [Architecture Decision Records](#11-architecture-decision-records)
12. [Glossary](#12-glossary)
13. [Traceability Matrix](#13-traceability-matrix)

---

## 1. Executive Summary

This document defines the complete implementation architecture for the Bench Test Traffic Light Controller (TLC). It translates the behavioral specification SYS-TLC-001 v1.0 into concrete hardware wiring decisions, software module decomposition, inter-module interfaces, state machine encoding, debounce algorithm, timing strategy, startup sequence, error handling behavior, and verifiable test criteria.

The system is implemented entirely on a Raspberry Pi with a 40-pin GPIO header. Three LEDs (red, yellow, green) driven from GPIO pins 17, 27, and 22 respectively represent the traffic signal. A single momentary push-button wired to GPIO 18 serves as the Crosswalk Request Button (CRB). No external microcontrollers, FPGAs, or additional logic devices are required.

The software is structured as a single-threaded polling loop executing at a 10 ms tick rate. This tick period yields a worst-case phase transition latency of 10 ms, which satisfies the 50 ms maximum specified by NF-005 with a 40 ms margin. All timing is performed by elapsed-time comparison against a monotonic clock, making the design immune to accumulated drift over the 8-hour continuous operation requirement of NF-008.

A developer implementing from this document alone shall be able to produce a correctly functioning system without reference to SYS-TLC-001 or this conversation.

---

## 2. Scope and System Boundary

### 2.1 In-Scope (This System)

- Raspberry Pi GPIO hardware configuration and wiring
- GPIO driver layer (pin configuration and read/write)
- Debounce module (stability timer and post-press lockout)
- State machine module (four-state FSM with CR flag)
- Timing module (monotonic clock elapsed-time measurement)
- Main control loop (orchestration of all modules)
- Startup sequence
- Undefined-state error handler

### 2.2 Out-of-Scope (External to This System)

- Operating system installation and configuration on the Raspberry Pi
- Python runtime installation
- Power supply design and regulation circuitry upstream of the Raspberry Pi's 5 V input
- LED module PCB layout (bench wiring is acceptable)
- Any networking, logging, or remote monitoring capability

### 2.3 External Interfaces at the Boundary

| Interface | Direction | Description |
|-----------|-----------|-------------|
| 5 V USB / barrel-jack power | In | Powers the Raspberry Pi and, through the Pi's 3.3 V regulator, the GPIO outputs |
| GPIO 17 output | Out | Drives red LED circuit |
| GPIO 27 output | Out | Drives yellow LED circuit |
| GPIO 22 output | Out | Drives green LED circuit |
| GPIO 18 input | In | Receives CRB signal |
| GND rail | Reference | Common ground shared by Pi and all LED/button circuits |

---

## 3. Functional Requirements

The following requirements are reproduced from SYS-TLC-001 v1.0 with stable identifiers. Each requirement is marked with the architecture component responsible for satisfying it.

| ID | Requirement Statement | Responsible Component |
|----|-----------------------|-----------------------|
| FR-001 | The system shall continuously cycle GREEN → YELLOW → RED → GREEN when no CR is pending. | State Machine Module |
| FR-002 | During GREEN: GPIO 22 ON; GPIO 17 OFF; GPIO 27 OFF. | State Machine Module, GPIO Driver |
| FR-003 | During YELLOW: GPIO 27 ON; GPIO 17 OFF; GPIO 22 OFF. | State Machine Module, GPIO Driver |
| FR-004 | During RED: GPIO 17 ON; GPIO 27 OFF; GPIO 22 OFF. | State Machine Module, GPIO Driver |
| FR-005 | Exactly one indicator illuminated at all times in steady state. | State Machine Module, GPIO Driver |
| FR-006 | Monitor CRB at all times, including during phase transitions. | Debounce Module, Main Loop |
| FR-007 | A single valid CRB press latches CR_PENDING = True. | Debounce Module, State Machine Module |
| FR-008 | Service pending CR by inserting PEDESTRIAN WALK between RED and subsequent GREEN. | State Machine Module |
| FR-009 | During PEDESTRIAN WALK: GPIO 17 ON; GPIO 27 OFF; GPIO 22 OFF. | State Machine Module, GPIO Driver |
| FR-010 | After PEDESTRIAN WALK completes, clear CR and resume from GREEN. | State Machine Module |
| FR-011 | Press during RED: complete full RED duration first, then PEDESTRIAN WALK. | State Machine Module |
| FR-012 | Press during PEDESTRIAN WALK: ignored; no extension; no new latch. | Debounce Module, State Machine Module |
| FR-013 | Multiple presses before service: only one PEDESTRIAN WALK inserted. | State Machine Module |
| FR-014 | Press during GREEN: latch CR, carry through YELLOW and RED, service after RED. | State Machine Module |
| FR-015 | Press during YELLOW: latch CR if not already latched, service after RED. | State Machine Module |
| FR-016 | Power-on: system enters GREEN immediately. | Main Loop, Startup Sequence |
| FR-017 | All indicators off < 500 ms before GREEN illuminates. | Startup Sequence, GPIO Driver |
| FR-018 | Debounce CRB so one physical press registers as exactly one logical press event. | Debounce Module |
| FR-019 | Reject CRB transitions stable < 50 ms. | Debounce Module |
| FR-020 | 300 ms post-press lockout after each valid press. | Debounce Module |

---

## 4. Non-Functional Requirements

| ID | Requirement Statement | Metric / Tolerance | Responsible Component |
|----|-----------------------|--------------------|-----------------------|
| NF-001 | GREEN phase duration: nominal 7 s, range 5–10 s. | 7000 ms ± 3000 ms | Timing Module |
| NF-002 | YELLOW phase duration: 3 s ± 100 ms. | 3000 ms ± 100 ms | Timing Module |
| NF-003 | RED phase duration: nominal 7 s, range 5–10 s. | 7000 ms ± 3000 ms | Timing Module |
| NF-004 | PEDESTRIAN WALK phase duration: 10 s ± 200 ms. | 10000 ms ± 200 ms | Timing Module |
| NF-005 | Phase transition latency ≤ 50 ms. | ≤ 50 ms | Main Loop, Timing Module |
| NF-006 | Debounce processing adds ≤ 100 ms latency between physical press and CR latch. | ≤ 100 ms | Debounce Module |
| NF-007 | Resume normal cycling after power interruption; no persistent state across power cycles. | Automatic on boot | Startup Sequence |
| NF-008 | 8 hours continuous operation without timing degradation. | 28800 s, drift ≤ 100 ms cumulative | Timing Module |
| NF-009 | Indicator state changes visually distinguishable at 2 m under standard indoor lighting. | Human-perceptible ON/OFF | GPIO Driver, LED circuit |
| NF-010 | No ambiguous indicator states outside defined 50 ms transition window. | Zero simultaneous ON events | State Machine Module, GPIO Driver |

---

## 5. Assumption and Open Question Resolution

### OQ-001 — PEDESTRIAN WALK blinking countdown

**Resolution:** The architecture implements a static red indicator for the full PEDESTRIAN WALK duration. No blink pattern is defined or implemented. Rationale: SYS-TLC-001 Section 3.2 explicitly places a dedicated pedestrian indicator out of scope. The red indicator is shared with the RED phase and adding a blink pattern would require additional state complexity without a stakeholder directive. If a blink requirement is added in a future revision of SYS-TLC-001, a new software sub-state and a GPIO toggle timer shall be added to the State Machine Module.

### OQ-002 — Operator reset mechanism

**Resolution:** No hardware reset button is implemented. The existing power cycling behavior (FR-016, FR-017, NF-007) is the defined reset mechanism for this prototype. Rationale: Adding a second button requires GPIO allocation, debounce logic, and state-machine handling that is not specified. This decision is recorded in ADR-005.

### OQ-003 — CR during PEDESTRIAN WALK: discard or queue

**Resolution:** Discard, consistent with FR-012. The architecture enforces CR_PENDING = False at all times while in state S4. A press during S4 is processed through the debounce module but the state machine evaluates FR-012 and takes no latch action. Rationale: Queueing would require multi-request tracking, contradicting FR-013's single-WALK guarantee per cycle. This is documented in ADR-006.

### OQ-004 — Phase duration acceptability for demonstration

**Resolution:** All durations are implemented at their nominal values as specified in NF-001 through NF-004 (GREEN = 7000 ms, YELLOW = 3000 ms, RED = 7000 ms, PEDESTRIAN WALK = 10000 ms). These are compile-time constants in the Timing Module. Adjustment requires only modifying four named constants and re-running the script; no architectural change is needed.

### OQ-005 — CR acknowledgment output to pedestrian

**Resolution:** No dedicated acknowledgment indicator is implemented. CR_PENDING is an internal software flag only. Rationale: No additional output pin or indicator is specified in SYS-TLC-001 Section 3.2. Hardware addition of an acknowledgment LED would require a GPIO pin allocation and is deferred pending stakeholder direction.

### AQ-001 — Python as the implementation language

**Assumption:** The software shall be implemented in Python 3 using the RPi.GPIO library (version 0.7.1 or later) or the gpiozero library (version 1.6.2 or later). Python 3 is pre-installed on Raspberry Pi OS (Bullseye or later). This assumption is documented because the timing analysis in Section 8.6 is predicated on Python's time.monotonic() function and loop characteristics. See ADR-001.

### AQ-002 — Operating system

**Assumption:** The Raspberry Pi runs Raspberry Pi OS (64-bit, Bullseye or later) with the default Linux kernel scheduler. The 10 ms tick design tolerates up to ±5 ms jitter from Linux scheduling without violating NF-005 (50 ms max latency). If a real-time kernel patch is applied, the tick period may be reduced to 5 ms for improved accuracy without any other architectural changes.

### AQ-003 — GPIO voltage level

**Assumption:** All Raspberry Pi GPIO pins operate at 3.3 V logic levels. GPIO outputs source/sink a maximum of 16 mA per pin and 50 mA total across all GPIO pins. The LED circuit in Section 7 is designed within these limits.

### AQ-004 — Button hardware

**Assumption:** The CRB is a standard normally-open momentary tactile pushbutton (e.g., ALPS SKHHAPA010 or equivalent). Contact bounce is confined to ≤ 20 ms as stated in SYS-TLC-001 A-002. The 50 ms stability threshold in FR-019 provides 30 ms margin above this.

---

## 6. System Architecture Overview

### 6.1 Block Diagram

```
+---------------------------------------------------+
|                  Raspberry Pi                     |
|                                                   |
|  +-------------+     +------------------+         |
|  | Main Loop   |---->| State Machine    |         |
|  | (10 ms tick)|     | Module           |         |
|  +------+------+     +--------+---------+         |
|         |                     |                   |
|         |            +--------v---------+         |
|         |            | GPIO Driver      |         |
|         |            | Layer            |         |
|         |            +--+---+---+---+--+         |
|         |               |   |   |   |            |
|  +------v------+        |   |   |   |            |
|  | Debounce    |        |   |   |   |            |
|  | Module      |        |   |   |   |            |
|  +------+------+        |   |   |   |            |
|         |               |   |   |   |            |
|  +------v------+        |   |   |   |            |
|  | Timing      |        |   |   |   |            |
|  | Module      |        |   |   |   |            |
|  +-------------+        |   |   |   |            |
|                          |   |   |   |            |
+--------------------------|---|---|---|------------+
                           |   |   |   |
              GPIO 17 (R)--+   |   |   |
              GPIO 27 (Y)------+   |   |
              GPIO 22 (G)----------+   |
              GPIO 18 (CRB input)------+
                           |   |   |
                         [R] [Y] [G]   [Button]
                         LED LED LED
```

### 6.2 Data Flow

```
Physical Button Press
        |
        v
GPIO 18 raw signal
        |
        v
[Debounce Module]
  - Stability timer (50 ms)
  - Lockout timer (300 ms)
        |
        v (valid_press_event: bool)
        |
[State Machine Module]
  - Evaluates current state + CR_PENDING + valid_press_event
  - Updates CR_PENDING flag
  - Evaluates phase elapsed time (from Timing Module)
  - Determines state transition
        |
        v (target_state: PhaseState)
        |
[GPIO Driver Layer]
  - Maps target_state to GPIO 17, 27, 22 on/off values
  - Writes GPIO pins atomically in sequence
        |
        v
Physical LED outputs (GPIO 17, 27, 22)
```

### 6.3 Control Flow (Main Loop)

```
POWER ON
    |
    v
[Startup Sequence]
  1. Initialize GPIO Driver (all pins LOW)
  2. Initialize Timing Module
  3. Initialize Debounce Module
  4. Initialize State Machine (state = S1_GREEN, CR_PENDING = False)
  5. Apply GPIO state for S1_GREEN
    |
    v
[Main Loop — 10 ms tick]
  Per tick, in order:
    1. Record tick_start = monotonic_clock()
    2. raw_input = gpio_driver.read_crb()
    3. valid_press = debounce.process(raw_input, tick_start)
    4. state_machine.update(valid_press, tick_start)
       a. If valid_press and state != S4: set CR_PENDING = True
       b. Evaluate phase elapsed time
       c. If phase elapsed: determine next state per transition table
       d. If state changed: call gpio_driver.apply_state(new_state)
    5. tick_elapsed = monotonic_clock() - tick_start
    6. sleep(max(0, TICK_PERIOD_MS - tick_elapsed) / 1000)
    |
    v (repeat forever)
```

---

## 7. Hardware Specifications

### 7.1 Platform

| Attribute | Specification |
|-----------|---------------|
| Platform | Raspberry Pi (any model with 40-pin GPIO header: Model 3B, 3B+, 4B, 5, Zero 2W, or later) |
| GPIO logic level | 3.3 V ± 5% (3.135 V minimum, 3.465 V maximum) |
| GPIO output drive | 8 mA nominal, 16 mA maximum per pin |
| GPIO total current budget | 50 mA maximum across all GPIO pins simultaneously |
| GPIO input threshold HIGH | ≥ 2.0 V |
| GPIO input threshold LOW | ≤ 0.8 V |
| Operating temperature | 0°C to 50°C ambient (bench environment) |

### 7.2 GPIO Pin Allocation Table

| GPIO BCM | 40-pin Header Pin | Direction | Function | Signal Level | Pull Config | Description |
|----------|-------------------|-----------|----------|--------------|-------------|-------------|
| GPIO 17 | Pin 11 | Output | Red LED drive | 3.3 V / 0 V | None (output) | HIGH = red LED ON; LOW = red LED OFF |
| GPIO 27 | Pin 13 | Output | Yellow LED drive | 3.3 V / 0 V | None (output) | HIGH = yellow LED ON; LOW = yellow LED OFF |
| GPIO 22 | Pin 15 | Output | Green LED drive | 3.3 V / 0 V | None (output) | HIGH = green LED ON; LOW = green LED OFF |
| GPIO 18 | Pin 12 | Input | CRB signal | 3.3 V / 0 V | Internal pull-up enabled | LOW = button pressed; HIGH = button released |
| GND | Pin 6 (or any GND) | Reference | Common ground | 0 V | N/A | Shared ground for all LED cathodes and button circuit |
| 3.3 V | Pin 1 (or Pin 17) | Supply | Reference only | 3.3 V | N/A | Not used to drive LED anodes — anodes driven from GPIO output pins directly |

**Pull configuration rationale (ADR-002):** GPIO 18 uses the Raspberry Pi's internal pull-up resistor (approximately 50 kΩ). The CRB is wired between GPIO 18 and GND. When the button is open, GPIO 18 reads HIGH (3.3 V through pull-up). When the button is pressed, GPIO 18 is pulled LOW (0 V through direct short to GND). This active-low configuration is preferred over an external pull-down because: (1) it eliminates an external resistor component, (2) the internal pull-up is sufficient to overcome leakage and noise on a short bench wire, and (3) active-low is the safer failure mode — a disconnected button reads HIGH (released), not spuriously pressed.

### 7.3 LED Circuit Specification

Each LED is connected in series with a current-limiting resistor between the respective GPIO output pin and GND.

**Design equations:**

```
V_GPIO_HIGH = 3.3 V (nominal)
V_F          = 2.0 V (typical red/yellow/green standard LED forward voltage)
I_LED_target = 5 mA (sufficient for 2 m visibility per NF-009; within GPIO drive budget)

R_series = (V_GPIO_HIGH - V_F) / I_LED_target
         = (3.3 V - 2.0 V) / 0.005 A
         = 1.3 V / 0.005 A
         = 260 Ω

Nearest standard resistor (E24 series): 270 Ω

Actual current at 270 Ω:
I = (3.3 V - 2.0 V) / 270 Ω = 4.81 mA  (within 16 mA GPIO limit)

Worst case (V_GPIO = 3.135 V, V_F = 1.8 V low-end red LED):
I_max = (3.135 V - 1.8 V) / 270 Ω = 4.94 mA  (acceptable)

Worst case (V_GPIO = 3.135 V, V_F = 2.4 V high-end green LED):
I_min = (3.135 V - 2.4 V) / 270 Ω = 2.72 mA  (still visible at 2 m)
```

**Specified resistor value:** 270 Ω ± 5%, 1/8 W minimum power rating (actual dissipation < 10 mW).

A value of 330 Ω is also acceptable if 270 Ω is unavailable; at 330 Ω and V_F = 2.0 V, LED current = 3.94 mA, which remains adequate for NF-009.

#### LED Wiring Table

| LED Color | Anode connection | Series Resistor | Cathode connection | GPIO BCM |
|-----------|------------------|-----------------|--------------------|----------|
| Red | GPIO 17 (Pin 11) | 270 Ω ± 5% | GND (Pin 6) | 17 |
| Yellow | GPIO 27 (Pin 13) | 270 Ω ± 5% | GND (Pin 6) | 27 |
| Green | GPIO 22 (Pin 15) | 270 Ω ± 5% | GND (Pin 6) | 22 |

#### Button Wiring Table

| Signal | Terminal 1 | Terminal 2 | Pull configuration |
|--------|-----------|-----------|-------------------|
| CRB | GPIO 18 (Pin 12) | GND (Pin 6) | Internal pull-up on GPIO 18 enabled in software |

### 7.4 Power Budget

| Source | Current draw | Notes |
|--------|-------------|-------|
| Raspberry Pi (idle, no peripherals) | 300–500 mA at 5 V | Platform baseline |
| One LED at 4.81 mA from 3.3 V rail | ~4.81 mA | Only one LED illuminated at a time (FR-005) |
| Total GPIO current (worst case) | 4.81 mA | Single LED active; button pull-up ≈ 66 µA (negligible) |
| Total system | < 550 mA at 5 V | Well within USB 2.4 A or dedicated 5 V 2.5 A supply |

### 7.5 Timing Constraints for GPIO Transitions

| Parameter | Value | Notes |
|-----------|-------|-------|
| GPIO output switching time (Raspberry Pi) | < 1 µs | Hardware-limited; negligible vs. 10 ms tick |
| Software GPIO write latency (RPi.GPIO library) | < 1 ms | Measured typical; within NF-005 budget |
| Target: all three LED GPIO writes complete | < 2 ms | Sequential write of three pins in software |

---

## 8. Software Architecture

### 8.1 Module Decomposition

The software is organized into five modules with well-defined responsibility boundaries:

```
tlc/
├── main.py              # Entry point; startup sequence and main loop
├── gpio_driver.py       # GPIO Driver Layer
├── debounce.py          # Debounce Module
├── state_machine.py     # State Machine Module
└── timing.py            # Timing Module
```

### 8.2 GPIO Driver Layer (`gpio_driver.py`)

**Responsibility:** Abstract all RPi.GPIO library calls. Provide named functions for pin initialization, LED output, and button input. No logic resides in this layer; it maps semantic commands to physical pin operations.

**Constants:**

```python
PIN_RED    = 17   # BCM numbering
PIN_YELLOW = 27   # BCM numbering
PIN_GREEN  = 22   # BCM numbering
PIN_CRB    = 18   # BCM numbering, input with internal pull-up
```

**API:**

```python
def gpio_init() -> None:
    """
    Initialize the GPIO subsystem.

    Preconditions:
        - RPi.GPIO library is installed and importable.
        - Script is running on a Raspberry Pi with BCM GPIO available.

    Postconditions:
        - GPIO numbering mode set to BCM.
        - GPIO 17, 27, 22 configured as outputs, initial state LOW (all LEDs OFF).
        - GPIO 18 configured as input with internal pull-up enabled.
        - No LED is illuminated after this call returns.

    Errors:
        - RuntimeError: raised if GPIO library cannot access hardware
          (e.g., not running on a Pi, or insufficient permissions).

    Thread safety: Not thread-safe. Call exactly once from the main thread
    before the main loop begins.

    Memory ownership: No allocation. GPIO state is held in hardware registers.

    Timing: Completes within 50 ms of being called. Called only at startup.
    """

def gpio_cleanup() -> None:
    """
    Release GPIO resources and reset all pins to safe state.

    Preconditions:
        - gpio_init() has been called.

    Postconditions:
        - All output pins set LOW (all LEDs OFF).
        - RPi.GPIO cleanup() called.

    Errors: None raised. Best-effort cleanup.

    Thread safety: Call from main thread only, after main loop exits.
    """

def gpio_set_leds(red: bool, yellow: bool, green: bool) -> None:
    """
    Set the state of all three LED output pins atomically in software.
    Writes GPIO 17, then GPIO 27, then GPIO 22 in that fixed order.
    Total write time shall be < 2 ms.

    Parameters:
        red    (bool): True = GPIO 17 HIGH (LED ON);  False = GPIO 17 LOW (LED OFF)
        yellow (bool): True = GPIO 27 HIGH (LED ON);  False = GPIO 27 LOW (LED OFF)
        green  (bool): True = GPIO 22 HIGH (LED ON);  False = GPIO 22 LOW (LED OFF)

    Preconditions:
        - gpio_init() has been called.

    Postconditions:
        - GPIO 17 reflects the value of `red`.
        - GPIO 27 reflects the value of `yellow`.
        - GPIO 22 reflects the value of `green`.

    Errors:
        - RuntimeError: if GPIO hardware write fails.

    Thread safety: Not thread-safe. Call only from the main loop thread.

    Constraint (FR-005): Caller is responsible for ensuring at most one of
    red, yellow, green is True at any call. This function does not enforce
    the constraint; it writes exactly what it is given.
    """

def gpio_read_crb() -> bool:
    """
    Read the instantaneous state of the Crosswalk Request Button.

    Returns:
        True  = button is currently PRESSED (GPIO 18 reads LOW, active-low).
        False = button is currently RELEASED (GPIO 18 reads HIGH).

    Preconditions:
        - gpio_init() has been called.

    Postconditions: None (read-only).

    Errors:
        - RuntimeError: if GPIO hardware read fails.

    Thread safety: Not thread-safe. Call only from the main loop thread.

    Note: The returned value is raw and unbounced. The Debounce Module is
    responsible for filtering this signal.
    """
```

### 8.3 Timing Module (`timing.py`)

**Responsibility:** Provide a monotonic elapsed-time query based on Python's `time.monotonic()`. This function returns seconds as a floating-point value with sub-millisecond resolution and is immune to wall-clock adjustments (NTP, DST, etc.), satisfying NF-008.

**Constants:**

```python
TICK_PERIOD_MS       = 10    # Main loop target period in milliseconds
TICK_PERIOD_S        = 0.010 # Main loop target period in seconds

DURATION_GREEN_MS    = 7000  # Nominal GREEN phase duration, milliseconds (NF-001)
DURATION_YELLOW_MS   = 3000  # Nominal YELLOW phase duration, milliseconds (NF-002)
DURATION_RED_MS      = 7000  # Nominal RED phase duration, milliseconds (NF-003)
DURATION_PED_MS      = 10000 # PEDESTRIAN WALK phase duration, milliseconds (NF-004)

DEBOUNCE_STABLE_MS   = 50    # CRB stability window, milliseconds (FR-019)
DEBOUNCE_LOCKOUT_MS  = 300   # Post-press lockout, milliseconds (FR-020)
```

**API:**

```python
def now_ms() -> float:
    """
    Return the current monotonic time in milliseconds as a float.

    Resolution: ≥ 1 ms (actual resolution is sub-millisecond on Linux).
    Monotonicity: strictly non-decreasing; immune to NTP or system clock changes.

    Returns:
        float: milliseconds since an arbitrary epoch (suitable only for
               elapsed-time calculations, not wall-clock display).

    Errors: None. time.monotonic() does not raise exceptions.

    Thread safety: Safe to call from any thread. Used only from the main loop.
    """

def elapsed_ms(start_ms: float) -> float:
    """
    Return the number of milliseconds elapsed since start_ms.

    Parameters:
        start_ms (float): A timestamp previously returned by now_ms().

    Returns:
        float: now_ms() - start_ms. Always >= 0.0 by monotonic guarantee.

    Errors: None.

    Preconditions:
        - start_ms was obtained from now_ms() in the same process instance.
    """
```

### 8.4 Debounce Module (`debounce.py`)

**Responsibility:** Accept a raw boolean button sample per tick and produce a valid_press_event output. Implement the two-stage algorithm: (1) 50 ms stability timer and (2) 300 ms post-press lockout.

**State held within Debounce module (internal):**

| Field | Type | Initial value | Description |
|-------|------|---------------|-------------|
| `_last_raw` | bool | False | Raw CRB reading from previous tick |
| `_stable_start_ms` | float or None | None | Monotonic time when the current stable LOW began; None if not timing |
| `_lockout_until_ms` | float or None | None | Monotonic time when lockout expires; None if no lockout active |

**Algorithm (executed once per tick):**

```
function debounce_process(raw_pressed: bool, tick_time_ms: float) -> bool:

    # Stage 0: Lockout check
    if _lockout_until_ms is not None:
        if tick_time_ms < _lockout_until_ms:
            # Still in lockout; ignore all input
            _last_raw = raw_pressed
            return False
        else:
            # Lockout expired
            _lockout_until_ms = None
            _stable_start_ms  = None

    # Stage 1: Stability detection
    if raw_pressed == True:
        if _last_raw == False:
            # Rising edge (active-low: button just went pressed)
            _stable_start_ms = tick_time_ms
        else:
            # Button remains pressed — check stability window
            if _stable_start_ms is not None:
                if elapsed_ms(_stable_start_ms) >= DEBOUNCE_STABLE_MS:
                    # Valid press confirmed
                    _lockout_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS
                    _stable_start_ms  = None
                    _last_raw = raw_pressed
                    return True  # Emit exactly one valid_press_event
    else:
        # Button released — cancel any pending stability timer
        _stable_start_ms = None

    _last_raw = raw_pressed
    return False
```

**Timing properties of this algorithm:**

- Minimum time from physical press to valid_press_event: 50 ms (DEBOUNCE_STABLE_MS), one tick resolution of 10 ms → 50 ms to 60 ms latency, satisfying NF-006 (≤ 100 ms).
- Maximum time: 60 ms (50 ms stability window + up to one 10 ms tick overshoot). Worst case is within NF-006.
- Post-press lockout: 300 ms minimum from moment of event emission. Subsequent bounces or holds during this window produce no output.
- The algorithm processes at most one valid_press_event per lockout period (300 ms), guaranteeing FR-018, FR-019, FR-020.

**API:**

```python
class DebounceModule:
    def __init__(self) -> None:
        """
        Initialize debounce state.

        Postconditions:
            - _last_raw = False
            - _stable_start_ms = None
            - _lockout_until_ms = None
        """

    def process(self, raw_pressed: bool, tick_time_ms: float) -> bool:
        """
        Process one raw CRB sample and return whether a valid press event occurred.

        Parameters:
            raw_pressed   (bool):  True = button physically pressed this tick.
            tick_time_ms  (float): Current monotonic time from now_ms().

        Returns:
            True  = a valid press event has been confirmed this tick (emit once per press).
            False = no valid press event this tick.

        Preconditions:
            - Called exactly once per main loop tick.
            - tick_time_ms is non-decreasing across calls.

        Postconditions:
            - Internal state updated per algorithm above.
            - Returns True at most once per lockout window (300 ms).

        Errors: None raised. Defensive: if tick_time_ms < previous tick_time_ms,
                treated as same tick (no elapsed time assumed).

        Thread safety: Not thread-safe. Call only from the main loop thread.

        Memory ownership: Internal state only. No heap allocation per call.
        """
```

### 8.5 State Machine Module (`state_machine.py`)

**Responsibility:** Maintain current phase state and CR_PENDING flag. Evaluate transition conditions each tick. Drive GPIO outputs via GPIO Driver when a transition occurs. Implement the error handler for undefined states (C-004).

#### 8.5.1 State Enumeration

```python
from enum import IntEnum

class PhaseState(IntEnum):
    S1_GREEN   = 1
    S2_YELLOW  = 2
    S3_RED     = 3
    S4_PED     = 4
    S_ERROR    = 99  # Undefined/fault state (C-004)
```

#### 8.5.2 Phase Duration Table

| State | Duration constant | Nominal value |
|-------|-------------------|---------------|
| S1_GREEN | DURATION_GREEN_MS | 7000 ms |
| S2_YELLOW | DURATION_YELLOW_MS | 3000 ms |
| S3_RED | DURATION_RED_MS | 7000 ms |
| S4_PED | DURATION_PED_MS | 10000 ms |

#### 8.5.3 GPIO Output Table (per state)

| State | GPIO 17 (Red) | GPIO 27 (Yellow) | GPIO 22 (Green) |
|-------|--------------|-----------------|----------------|
| S1_GREEN | LOW (OFF) | LOW (OFF) | HIGH (ON) |
| S2_YELLOW | LOW (OFF) | HIGH (ON) | LOW (OFF) |
| S3_RED | HIGH (ON) | LOW (OFF) | LOW (OFF) |
| S4_PED | HIGH (ON) | LOW (OFF) | LOW (OFF) |
| S_ERROR | HIGH (ON) | LOW (OFF) | LOW (OFF) |

#### 8.5.4 State Transition Table (formal)

| Current State | Condition | Next State | Action |
|---------------|-----------|------------|--------|
| S1_GREEN | elapsed ≥ DURATION_GREEN_MS | S2_YELLOW | Apply YELLOW GPIO; reset phase timer |
| S2_YELLOW | elapsed ≥ DURATION_YELLOW_MS | S3_RED | Apply RED GPIO; reset phase timer |
| S3_RED | elapsed ≥ DURATION_RED_MS AND CR_PENDING = False | S1_GREEN | Apply GREEN GPIO; reset phase timer |
| S3_RED | elapsed ≥ DURATION_RED_MS AND CR_PENDING = True | S4_PED | Set CR_PENDING = False; Apply RED GPIO (unchanged); reset phase timer |
| S4_PED | elapsed ≥ DURATION_PED_MS | S1_GREEN | Apply GREEN GPIO; reset phase timer |
| Any state | valid_press_event AND current state = S4_PED | (same state) | Discard press; no state change; no CR latch (FR-012) |
| Any state | valid_press_event AND current state ≠ S4_PED AND CR_PENDING = False | (same state) | Set CR_PENDING = True; no state change |
| Any state | valid_press_event AND CR_PENDING = True | (same state) | Discard press; CR already latched (FR-013) |
| S_ERROR | (any) | S_ERROR | Remain halted; red only illuminated (C-004) |

#### 8.5.5 State Machine Data Structure

```python
@dataclass
class StateMachineState:
    current_state:    PhaseState  = PhaseState.S1_GREEN
    cr_pending:       bool        = False
    phase_start_ms:   float       = 0.0  # now_ms() at the moment current state was entered
```

#### 8.5.6 API

```python
class StateMachine:
    def __init__(self, gpio: GPIODriver) -> None:
        """
        Initialize state machine.

        Parameters:
            gpio: An initialized GPIODriver instance. The state machine owns
                  all calls to gpio.gpio_set_leds() after initialization.

        Postconditions:
            - current_state = S1_GREEN (FR-016)
            - cr_pending = False
            - phase_start_ms = 0.0 (set properly on first update() call)
            - GPIO outputs NOT yet set. Caller (startup sequence) sets initial
              GPIO state by calling apply_state() after constructing this object.

        Errors: None.
        """

    def initialize(self, tick_time_ms: float) -> None:
        """
        Set the phase start timestamp and apply initial GPIO state.
        Must be called once, immediately after __init__, before the main loop.

        Parameters:
            tick_time_ms (float): Current monotonic time from now_ms().

        Postconditions:
            - phase_start_ms = tick_time_ms
            - GPIO set for S1_GREEN: GPIO 22 HIGH, GPIO 17 LOW, GPIO 27 LOW.

        Errors:
            - RuntimeError: propagated from gpio.gpio_set_leds() on hardware failure.
        """

    def update(self, valid_press_event: bool, tick_time_ms: float) -> PhaseState:
        """
        Execute one state machine tick.

        Parameters:
            valid_press_event (bool):  True if the Debounce Module confirmed a
                                       press this tick.
            tick_time_ms      (float): Current monotonic time from now_ms().

        Returns:
            PhaseState: The current state after this tick's evaluation.

        Processing order (within one call):
            1. If valid_press_event:
               a. If current_state == S4_PED: discard (FR-012). Do nothing.
               b. Else if cr_pending == False: set cr_pending = True.
               c. Else: discard (FR-013, already latched).
            2. Compute elapsed = elapsed_ms(phase_start_ms).
            3. Evaluate transition conditions per Section 8.5.4.
            4. If transition occurs:
               a. Set current_state = next_state.
               b. If transitioning into S4_PED from S3_RED: set cr_pending = False (FR-010).
               c. Set phase_start_ms = tick_time_ms.
               d. Call gpio.gpio_set_leds() with values for new state.
            5. Return current_state.

        Preconditions:
            - initialize() has been called.
            - tick_time_ms >= phase_start_ms.

        Postconditions:
            - current_state reflects any transition that occurred.
            - GPIO pins reflect current_state.
            - cr_pending is updated per processing rules above.

        Errors:
            - If current_state is not a recognized PhaseState member:
              enter_error_state() is called. RuntimeError may be raised
              to halt the process (see enter_error_state()).

        Thread safety: Not thread-safe. Call only from the main loop thread.

        Memory ownership: No heap allocation per call.
        """

    def enter_error_state(self) -> None:
        """
        Transition to S_ERROR state per C-004.

        Postconditions:
            - current_state = S_ERROR.
            - GPIO 17 HIGH (red ON); GPIO 27 LOW; GPIO 22 LOW.
            - cr_pending = False.
            - phase_start_ms unchanged (no further transitions evaluated).
            - Raises RuntimeError("TLC entered undefined state — red only, halted")
              to terminate the main loop, requiring power cycle to recover.

        Note: The raised RuntimeError shall propagate through main.py and
        terminate the process. The OS will keep GPIO in the last-written state
        until gpio_cleanup() is called by a finally block in main.py.
        """
```

### 8.6 Main Loop Module (`main.py`)

**Responsibility:** Orchestrate startup sequence and run the 10 ms main loop calling modules in defined order. Catch RuntimeError from enter_error_state() and perform clean shutdown.

#### 8.6.1 Startup Sequence (FR-016, FR-017)

The following steps shall execute in order. Total elapsed time from step 1 to step 7 shall be < 500 ms (FR-017).

| Step | Action | Timing constraint |
|------|--------|-------------------|
| 1 | `gpio_init()` — configure pins, all LEDs LOW | Completes within 50 ms |
| 2 | `t0 = now_ms()` — record startup timestamp | Instantaneous |
| 3 | Construct `DebounceModule()` — initialize debounce state | Instantaneous |
| 4 | Construct `StateMachine(gpio)` — initialize FSM | Instantaneous |
| 5 | `t1 = now_ms()` — record pre-green timestamp | Instantaneous |
| 6 | `state_machine.initialize(t1)` — set S1_GREEN GPIO outputs and phase_start_ms | GPIO write < 2 ms |
| 7 | Assert `(t1 - t0) < 500 ms` — FR-017 compliance check | Log warning if violated; do not halt |
| 8 | Enter main loop | — |

Between step 1 (all LEDs OFF) and step 6 (GREEN ON), total time is the duration of steps 2–5: negligible Python object construction, well under 10 ms. FR-017 (all indicators off < 500 ms) is satisfied with substantial margin.

#### 8.6.2 Main Loop Structure

```python
TICK_PERIOD_S = 0.010  # 10 ms

try:
    while True:
        tick_start_ms = now_ms()

        # 1. Sample button
        raw_pressed = gpio_read_crb()

        # 2. Debounce
        valid_press = debounce.process(raw_pressed, tick_start_ms)

        # 3. State machine update (GPIO written inside if transition occurs)
        state_machine.update(valid_press, tick_start_ms)

        # 4. Sleep remainder of tick period
        tick_elapsed_s = (now_ms() - tick_start_ms) / 1000.0
        sleep_s = max(0.0, TICK_PERIOD_S - tick_elapsed_s)
        time.sleep(sleep_s)

except RuntimeError as e:
    # C-004: undefined state — red already illuminated by enter_error_state()
    # Log the error; remain in red-only state until power cycle.
    print(f"[FATAL] {e}", flush=True)
    # Do not call gpio_cleanup() here — leave red LED on as fault indicator.
    sys.exit(1)

finally:
    gpio_cleanup()
```

#### 8.6.3 Tick Rate Analysis and NF-005 Compliance

**Tick period:** 10 ms (TICK_PERIOD_MS)

**Worst-case transition latency calculation:**

A phase timer expires at an arbitrary point within a 10 ms tick. In the worst case, the timer expires 1 µs after a tick begins, meaning the next evaluation of the elapsed time occurs at the start of the following tick — 10 ms later.

```
Worst-case latency breakdown:
  - Tick polling overshoot:                 10 ms  (one full tick before detection)
  - State machine evaluation time:           < 1 ms
  - gpio_set_leds() execution time:          < 2 ms
  - time.sleep() scheduling jitter (Linux):  ± 5 ms (conservative)
  -----------------------------------------------
  Total worst case:                         < 18 ms
```

18 ms is well within the 50 ms limit of NF-005, providing a 32 ms margin.

**Drift analysis for NF-008:**

`time.monotonic()` is implemented on Linux via `CLOCK_MONOTONIC`, which is disciplined by the kernel's NTP loop to < 1 ms/hour drift. Over 8 hours:

```
Maximum drift = 1 ms/hour × 8 hours = 8 ms cumulative
```

8 ms drift over 8 hours is imperceptible relative to the 100 ms tolerance on YELLOW (NF-002) and 200 ms tolerance on PEDESTRIAN WALK (NF-004). NF-008 is satisfied.

### 8.7 State Machine Formal State Diagram

```
                        [POWER ON]
                             |
                             v
                      +-------------+
               +----->|  S1_GREEN   |<-----+
               |      | GPIO22 ON   |      |
               |      +------+------+      |
               |             |             |
               |    elapsed >= 7000 ms     |
               |             |             |
               |             v             |
               |      +-------------+      |
               |      |  S2_YELLOW  |      |
               |      | GPIO27 ON   |      |
               |      +------+------+      |
               |             |             |
               |    elapsed >= 3000 ms     |
               |             |             |
               |             v             |
               |      +-------------+      |
               |      |   S3_RED    |      |
               |      | GPIO17 ON   |      |
               |      +------+------+      |
               |             |             |
               |    elapsed >= 7000 ms     |
               |       /           \       |
               |  CR=False        CR=True  |
               |    /                 \    |
  (no walk) ---+                      v   |
                               +-------------+
                               |   S4_PED    |
                               | GPIO17 ON   |
                               +------+------+
                                      |
                             elapsed >= 10000 ms
                                      |
                               CR_PENDING = False
                                      |
                                      +-----------> S1_GREEN (above)


  CRB press rules (applied in any state at valid_press_event):
    In S4_PED:              IGNORED (FR-012)
    In S1/S2/S3, CR=False:  CR_PENDING = True
    In S1/S2/S3, CR=True:   IGNORED (FR-013)

  Undefined state detected:
    --> S_ERROR: GPIO17 ON only; raise RuntimeError; halt
```

### 8.8 Error and Undefined State Handling (C-004)

If `StateMachine.update()` is called with `current_state` holding a value not in `{S1_GREEN, S2_YELLOW, S3_RED, S4_PED}`, the following behavior is mandatory:

1. Call `gpio_set_leds(red=True, yellow=False, green=False)` — illuminate red only.
2. Set `current_state = S_ERROR`.
3. Set `cr_pending = False`.
4. Raise `RuntimeError("TLC entered undefined state — red only, halted")`.

This RuntimeError propagates to the main loop's `except RuntimeError` handler, which prints the error and exits. The red LED remains illuminated (GPIO 17 HIGH) because `gpio_cleanup()` is NOT called in the error path — the `finally` block in the error-halt path shall call `gpio_cleanup()` only after OS signal (e.g., SIGINT from operator). A separate `sys.exit(1)` call in the `except` block precedes the `finally` in normal operator-terminated exit.

**Recovery:** Requires power cycle. On restart, the normal startup sequence re-enters S1_GREEN with no CR_PENDING (NF-007, Edge Case F).

---

## 9. Integration Contracts

### IC-001: GPIO Driver ↔ Physical LED Hardware

**Contract ID:** IC-001
**Producer:** GPIO Driver Layer (`gpio_driver.py`)
**Consumer:** Physical LED circuits (red, yellow, green)
**Interface Type:** Hardware — 3.3 V digital output, DC driven

**Behavioral Contract:**

- When `gpio_set_leds(red=True, yellow=False, green=False)` is called, GPIO 17 shall transition HIGH within 2 ms. GPIO 27 and GPIO 22 shall be LOW within 2 ms of the same call.
- The red LED shall illuminate to full brightness within 1 ms of GPIO 17 going HIGH (LED response time << 1 ms).
- At most one of GPIO 17, 27, 22 shall be HIGH at any time (enforced by State Machine Module caller).
- When `gpio_set_leds(False, False, False)` is called (startup and cleanup), all three pins shall be LOW within 2 ms.

**Failure Modes:**

| Failure | Producer behavior | Consumer behavior |
|---------|-------------------|-------------------|
| GPIO 17 write fails (hardware fault) | RuntimeError raised; enter_error_state() called | Red LED may not illuminate; fault condition |
| LED open circuit | GPIO output remains functional at commanded voltage | LED dark; NF-009 violated; bench fault |
| LED short circuit | GPIO current exceeds 16 mA limit; Pi GPIO may latch-up | Overcurrent; series resistor limits to < 12 mA at 3.3 V even with V_F = 0 V |
| GPIO pin stuck HIGH | LED permanently ON regardless of command | NF-010 violated; FR-005 violated |

**Performance SLA:** GPIO write to LED illumination change: < 2 ms (NF-005 sub-budget).

**Versioning:** Hardware wiring is fixed for this prototype. Changes to pin assignments require updates to PIN_RED, PIN_YELLOW, PIN_GREEN constants in `gpio_driver.py` and the GPIO Pin Allocation Table (Section 7.2).

---

### IC-002: GPIO Driver ↔ CRB Hardware

**Contract ID:** IC-002
**Producer:** Physical CRB hardware (button + pull-up)
**Consumer:** GPIO Driver Layer (`gpio_read_crb()`)
**Interface Type:** Hardware — 3.3 V digital input, active-low, internal pull-up

**Behavioral Contract:**

- Button released: GPIO 18 = HIGH (3.3 V through ~50 kΩ pull-up). `gpio_read_crb()` returns False.
- Button pressed: GPIO 18 = LOW (0 V, shorted to GND). `gpio_read_crb()` returns True.
- Contact bounce may produce up to 20 ms of transitions after a press or release. The GPIO Driver Layer returns the instantaneous value; filtering is the Debounce Module's responsibility.

**Failure Modes:**

| Failure | Producer behavior | Consumer behavior |
|---------|-------------------|-------------------|
| Button wire disconnected | GPIO 18 reads HIGH permanently (pull-up) | CR never latched; safe failure |
| Button wire shorted to GND | GPIO 18 reads LOW permanently | Debounce module sees permanent press; lockout keeps re-triggering every 300 ms; repeated CR latches — system inserts PEDESTRIAN WALK every cycle |
| GPIO 18 stuck HIGH | No button input detectable | CR never latched; safe failure |

**Performance SLA:** `gpio_read_crb()` completes within 1 ms per call.

---

### IC-003: Debounce Module ↔ State Machine Module

**Contract ID:** IC-003
**Producer:** Debounce Module (`debounce.py`)
**Consumer:** State Machine Module (`state_machine.py`)
**Interface Type:** Software — boolean return value, in-process, same thread

**Behavioral Contract:**

- `debounce.process()` returns True at most once per 300 ms lockout window.
- True is returned exactly once for each qualifying physical press (button stable LOW for ≥ 50 ms).
- The state machine shall call `debounce.process()` exactly once per tick, every tick, regardless of current phase state (FR-006).
- The state machine consumes the returned boolean by evaluating FR-012 / FR-013 / latch logic within the same tick.

**Failure Modes:**

| Failure | Producer behavior | Consumer behavior |
|---------|-------------------|-------------------|
| `process()` called with decreasing tick_time_ms | Treats as zero elapsed; stability timer effectively paused | No valid press emitted during anomalous period; recovery on next normal tick |
| `process()` not called for > 300 ms (tick stall) | State unchanged; lockout may linger past expiry | No events emitted; debounce resets correctly on next call |

**Performance SLA:** `process()` completes within 1 ms per call. Latency from physical press to True return: 50 ms minimum, 60 ms maximum (NF-006 budget: 100 ms).

---

### IC-004: State Machine Module ↔ GPIO Driver Layer

**Contract ID:** IC-004
**Producer:** State Machine Module
**Consumer:** GPIO Driver Layer
**Interface Type:** Software — function call, in-process, same thread

**Behavioral Contract:**

- `gpio_set_leds()` is called by the State Machine exactly once per state transition.
- It is NOT called on ticks where no transition occurs (GPIO pins are not re-written every tick).
- The state machine guarantees that the combination of (red, yellow, green) arguments always satisfies the mapping in Section 8.5.3: exactly one True value (except in S_ERROR which also has exactly one True value).
- The state machine calls `gpio_set_leds()` before returning from `update()`, so GPIO reflects the new state within the same tick that the transition is detected.

**Performance SLA:** Total time from phase timer expiry detection to GPIO write completion: < 3 ms (NF-005 sub-budget).

---

### IC-005: Timing Module ↔ All Modules

**Contract ID:** IC-005
**Producer:** Timing Module (`timing.py`)
**Consumer:** Debounce Module, State Machine Module, Main Loop
**Interface Type:** Software — function call returning float, in-process

**Behavioral Contract:**

- `now_ms()` returns a strictly non-decreasing float representing milliseconds.
- All callers within the same tick shall use the tick_start_ms captured at the top of the loop; they shall NOT call `now_ms()` independently within a tick (prevents inconsistent elapsed-time calculations across modules within the same tick).
- `elapsed_ms(start_ms)` is a pure function with no side effects.

**Performance SLA:** `now_ms()` completes within 0.1 ms per call.

---

## 10. Test Specification

### TC-001 — Normal Cycle, No CR (FR-001 through FR-005, NF-001 through NF-003)

**Test Type:** Integration / System

**Preconditions:**
- System powered on and running.
- CRB not pressed during test.
- Stopwatch available with 100 ms resolution.

**Test Steps:**
1. Apply power. Observe GREEN illuminates.
2. Measure duration from GREEN illumination to YELLOW illumination.
3. Verify only yellow LED is illuminated during YELLOW phase.
4. Measure duration from YELLOW illumination to RED illumination.
5. Verify only red LED is illuminated during RED phase.
6. Measure duration from RED illumination to GREEN illumination.
7. Verify only green LED is illuminated during GREEN phase.
8. Repeat steps 2–7 for three complete cycles.

**Stimulus:** No CRB input.

**Expected Response:**

| Measurement | Pass Criterion |
|-------------|----------------|
| GREEN phase duration | 5000 ms ≤ measured ≤ 10000 ms; nominal 7000 ms |
| YELLOW phase duration | 2900 ms ≤ measured ≤ 3100 ms |
| RED phase duration | 5000 ms ≤ measured ≤ 10000 ms; nominal 7000 ms |
| Indicator during GREEN | GPIO 22 HIGH only; GPIO 17 LOW; GPIO 27 LOW |
| Indicator during YELLOW | GPIO 27 HIGH only; GPIO 17 LOW; GPIO 22 LOW |
| Indicator during RED | GPIO 17 HIGH only; GPIO 27 LOW; GPIO 22 LOW |
| Two indicators simultaneously ON | Never occurs (FR-005) |

**Pass/Fail Criteria:** All six rows in the table above must pass for all three measured cycles.

**Required Equipment:** Logic analyzer or oscilloscope on GPIO 17, 27, 22 (recommended); stopwatch acceptable for manual validation.

---

### TC-002 — Startup Sequence (FR-016, FR-017)

**Test Type:** Integration

**Preconditions:**
- System powered off.
- Oscilloscope probe on GPIO 22 (green LED output).
- Second probe on GPIO 17 or 27 (optional, verify both are LOW at startup).

**Test Steps:**
1. Apply power.
2. Measure time from power application to GPIO 22 going HIGH.
3. Verify GPIO 17 and GPIO 27 remain LOW throughout.

**Stimulus:** Power application.

**Expected Response:**
- GPIO 22 shall go HIGH within 500 ms of power application.
- GPIO 17 and GPIO 27 shall remain LOW at all times from power application to first GREEN illumination.

**Pass/Fail Criteria:** Time to GREEN ≤ 500 ms. Zero spurious HIGH events on GPIO 17 or GPIO 27 before first GREEN.

---

### TC-003 — CRB Press During GREEN Phase (FR-007, FR-008, FR-014, Edge Case E)

**Test Type:** Integration / System

**Preconditions:**
- System in S1_GREEN phase, approximately 2 s into phase.
- No prior CR pending.

**Test Steps:**
1. Press and hold CRB for 200 ms (well above 50 ms debounce threshold).
2. Release CRB.
3. Observe GREEN phase continues for its remaining duration.
4. Observe YELLOW phase for full 3 s.
5. Observe RED phase for full 7 s (nominal).
6. Verify PEDESTRIAN WALK phase (red LED only) follows RED.
7. Measure PEDESTRIAN WALK duration.
8. Verify GREEN phase follows PEDESTRIAN WALK.
9. Verify CR_PENDING is cleared (subsequent cycles proceed without PEDESTRIAN WALK).

**Stimulus:** Single 200 ms CRB press at approximately t=2 s into GREEN phase.

**Expected Response:**

| Observable | Pass Criterion |
|------------|----------------|
| GREEN phase uninterrupted | Duration 5–10 s, not cut short |
| YELLOW follows GREEN | 2900–3100 ms |
| RED follows YELLOW | 5000–10000 ms; not cut short |
| PEDESTRIAN WALK follows RED | Red LED only; 9800–10200 ms |
| GREEN follows PEDESTRIAN WALK | GREEN resumes; no second PEDESTRIAN WALK |

---

### TC-004 — CRB Press During YELLOW Phase (FR-015, Edge Case A)

**Test Type:** Integration

**Preconditions:**
- System enters S2_YELLOW phase.
- No CR pending.

**Test Steps:**
1. At approximately 1 s into YELLOW phase, press CRB for 200 ms then release.
2. Observe YELLOW continues to completion.
3. Observe RED phase for full duration.
4. Verify PEDESTRIAN WALK follows RED.

**Stimulus:** Single 200 ms CRB press at t=1 s into YELLOW.

**Expected Response:** Identical to TC-003 from step 4 onward. YELLOW phase shall not be shortened.

---

### TC-005 — CRB Press During RED Phase (FR-011, Edge Case D)

**Test Type:** Integration

**Preconditions:**
- System enters S3_RED phase.
- No CR pending.

**Test Steps:**
1. At approximately 1 s into RED phase, press CRB for 200 ms then release.
2. Observe RED continues for its remaining scheduled duration (total = 7 s nominal).
3. Verify PEDESTRIAN WALK follows immediately after RED.

**Stimulus:** Single 200 ms CRB press at t=1 s into RED.

**Expected Response:**
- RED phase shall complete its full nominal 7000 ms duration before transitioning.
- PEDESTRIAN WALK shall follow without intervening GREEN phase.
- PEDESTRIAN WALK duration: 9800–10200 ms.

---

### TC-006 — CRB Press During PEDESTRIAN WALK Phase Ignored (FR-012, Edge Case B)

**Test Type:** Integration

**Preconditions:**
- System enters S4_PED phase (via prior CR press).

**Test Steps:**
1. At approximately 2 s into PEDESTRIAN WALK, press CRB for 200 ms then release.
2. Observe PEDESTRIAN WALK continues for its full duration (not extended).
3. Observe GREEN follows PEDESTRIAN WALK.
4. Observe GREEN → YELLOW → RED cycle occurs without additional PEDESTRIAN WALK.

**Stimulus:** Single 200 ms CRB press during PEDESTRIAN WALK.

**Expected Response:**
- PEDESTRIAN WALK duration: 9800–10200 ms (not extended).
- Subsequent cycle: GREEN → YELLOW → RED → GREEN (no S4_PED insertion).

---

### TC-007 — Multiple CRB Presses, Single PEDESTRIAN WALK (FR-013, Edge Case C)

**Test Type:** Integration

**Preconditions:**
- System in S1_GREEN phase.
- No CR pending.

**Test Steps:**
1. Press CRB at t=1 s into GREEN. Hold 200 ms.
2. Wait 500 ms (lockout expires).
3. Press CRB again. Hold 200 ms.
4. Observe full GREEN → YELLOW → RED cycle.
5. Verify exactly one PEDESTRIAN WALK phase follows RED.
6. Verify GREEN resumes after one PEDESTRIAN WALK (no second walk).

**Stimulus:** Two CRB presses during GREEN phase (separated by 500 ms).

**Expected Response:** Exactly one PEDESTRIAN WALK phase (9800–10200 ms). No second PEDESTRIAN WALK in the immediately following cycle.

---

### TC-008 — Debounce: Bounce Rejection (FR-018, FR-019)

**Test Type:** Unit / Integration

**Preconditions:**
- System in S1_GREEN phase, no CR pending.
- Signal generator or test harness capable of producing GPIO 18 pulses of defined duration.

**Test Steps:**
1. Apply 20 ms LOW pulse to GPIO 18 (simulated bounce, below 50 ms threshold).
2. Return GPIO 18 to HIGH.
3. Observe that CR_PENDING remains False after 100 ms.
4. Apply 49 ms LOW pulse to GPIO 18.
5. Return to HIGH.
6. Observe that CR_PENDING remains False.
7. Apply 55 ms LOW pulse to GPIO 18 (above threshold).
8. Observe that CR_PENDING becomes True within 100 ms of step 7.

**Stimulus:** GPIO 18 controlled by signal generator.

**Expected Response:**
- 20 ms pulse: no CR latch.
- 49 ms pulse: no CR latch.
- 55 ms pulse: CR latch within 100 ms (NF-006).

---

### TC-009 — Debounce: Post-Press Lockout (FR-020)

**Test Type:** Unit / Integration

**Preconditions:**
- System in S1_GREEN, no CR pending.
- Signal generator on GPIO 18.

**Test Steps:**
1. Apply 55 ms LOW pulse → CR latch occurs.
2. Wait 100 ms.
3. Apply second 55 ms LOW pulse (at t=155 ms from step 1 — within 300 ms lockout window).
4. Verify no second CR event emitted (CR_PENDING already True; lockout active).
5. Wait until t=400 ms from step 1 (lockout expired).
6. Apply 55 ms LOW pulse.
7. Verify debounce accepts press (lockout cleared; since CR_PENDING already True, press discarded by FSM per FR-013 — this is acceptable behavior).

**Stimulus:** Controlled GPIO 18 pulses with defined inter-press timing.

**Expected Response:**
- Step 3 pulse produces no additional event (lockout rejects it).
- Step 6 pulse is accepted by debounce (lockout expired).

---

### TC-010 — Phase Transition Latency (NF-005)

**Test Type:** Performance

**Preconditions:**
- Logic analyzer connected to GPIO 17, 27, 22.
- Logic analyzer sampling at ≥ 1 kHz (1 ms resolution).
- System running in normal cycle.

**Test Steps:**
1. Arm logic analyzer trigger on any GPIO pin edge.
2. Run system for at least 10 complete cycles.
3. Capture all transitions on GPIO 17, 27, 22.
4. For each captured transition: compute time between phase timer expiry (determined by configured phase duration) and the observed GPIO edge.

**Stimulus:** Normal operation, no CRB press.

**Expected Response:**
- All measured transition latencies ≤ 50 ms (NF-005).
- Typical measured latency: < 20 ms.

**Pass/Fail Criteria:** 100% of transitions (across 10 cycles × 3 transitions/cycle = 30 transitions minimum) shall show latency ≤ 50 ms.

---

### TC-011 — Power Interruption Recovery (NF-007, Edge Case F)

**Test Type:** System / Fault Injection

**Preconditions:**
- System running with CR_PENDING = True (achieved by pressing CRB during GREEN).
- System currently in S2_YELLOW phase (CR carried forward, walk not yet serviced).

**Test Steps:**
1. Remove power while in YELLOW phase with CR_PENDING = True.
2. All LEDs extinguish (observe immediately).
3. Restore power.
4. Observe GREEN phase illuminates within 500 ms.
5. Observe subsequent cycle runs GREEN → YELLOW → RED → GREEN without PEDESTRIAN WALK insertion (CR lost on power cycle).

**Stimulus:** Power interruption during YELLOW phase with pending CR.

**Expected Response:**
- Green LED illuminates within 500 ms of power restoration.
- No PEDESTRIAN WALK phase occurs in the first complete cycle after restoration.

---

### TC-012 — Eight-Hour Continuous Operation (NF-008)

**Test Type:** Stress / Endurance

**Preconditions:**
- Logic analyzer or automated test harness recording all GPIO transitions.
- System started from power-on.

**Test Steps:**
1. Start system. Begin recording.
2. At t=1 hour, 4 hours, and 8 hours: sample five consecutive YELLOW phase durations.
3. Compare measured durations to 3000 ms ± 100 ms.

**Stimulus:** Continuous normal cycling operation for 8 hours.

**Expected Response:**
- At each sample point, all five YELLOW measurements fall within 2900–3100 ms.
- No timing drift accumulation exceeding 100 ms observed between t=0 and t=8 hours.

**Pass/Fail Criteria:** All YELLOW phase measurements at all three sample points within tolerance.

---

### TC-013 — Undefined State Error Handler (C-004)

**Test Type:** Fault Injection / Unit

**Preconditions:**
- Test harness with ability to directly set `state_machine.current_state` to an out-of-range value (e.g., 99 mapped to a non-S_ERROR IntEnum value, or 0).

**Test Steps:**
1. Run system to stable GREEN phase.
2. Inject `current_state = 0` (not a valid PhaseState member) directly via test harness.
3. Allow one tick to execute.
4. Observe GPIO 17 HIGH, GPIO 27 LOW, GPIO 22 LOW.
5. Observe RuntimeError raised and process exits with code 1.
6. Verify GPIO 17 remains HIGH after process exit (OS retains last GPIO state).

**Stimulus:** Injected invalid state_machine.current_state = 0.

**Expected Response:**
- Red LED illuminates within one tick (≤ 10 ms).
- Process terminates with RuntimeError message containing "undefined state".
- GPIO 17 remains HIGH until explicit cleanup.

---

## 11. Architecture Decision Records

### ADR-001 — Software Implementation Language: Python 3

**Status:** Decided

**Context:** The hardware platform is a Raspberry Pi running Raspberry Pi OS. Multiple languages are available: C, C++, Python 3, and others. A choice must be made to enable a consistent software architecture.

**Options Considered:**
1. **C with WiringPi or pigpio:** Native performance, minimal latency, deterministic timing. Requires compilation, manual memory management, and more verbose code.
2. **Python 3 with RPi.GPIO or gpiozero:** High-level, rapid development, excellent Raspberry Pi community support. CPython interpreter overhead and GIL present; `time.monotonic()` provides adequate timing resolution.

**Decision:** Python 3 with the RPi.GPIO library.

**Rationale:** The 10 ms tick period provides 40 ms of margin against the 50 ms NF-005 limit. Python's `time.sleep()` and `time.monotonic()` are sufficient for the timing resolution required. Python reduces implementation risk and development time for a bench prototype. The GIL is not a concern because the design is intentionally single-threaded.

**Consequences:** C implementation could reduce transition latency to < 1 ms. If NF-005 were tightened to < 5 ms in a future revision, C would be required. All timing constants are defined as named Python constants, enabling straightforward porting.

---

### ADR-002 — CRB Wiring: Active-Low with Internal Pull-Up

**Status:** Decided

**Context:** The CRB must be detected by GPIO 18. Two standard approaches exist: active-low (button to GND, pull-up resistor) and active-high (button to 3.3 V, pull-down resistor).

**Options Considered:**
1. **Active-low with internal pull-up:** Button connects GPIO 18 to GND. Pi's internal ~50 kΩ pull-up holds GPIO 18 HIGH when button is open. Pressed = LOW. No external resistor needed.
2. **Active-high with external pull-down:** Button connects GPIO 18 to 3.3 V. External 10 kΩ pull-down holds GPIO 18 LOW when open. Pressed = HIGH. Requires one additional component.

**Decision:** Active-low with internal pull-up (Option 1).

**Rationale:** Eliminates external pull-down resistor (simpler bench wiring). Fail-safe: a disconnected or broken button wire results in GPIO 18 permanently HIGH (released state), which cannot trigger spurious CR events. The internal 50 kΩ pull-up is adequate for bench-length wires (< 30 cm). The software debounce module accounts for the active-low polarity in its `raw_pressed` inversion.

**Consequences:** The `gpio_read_crb()` function inverts the GPIO reading: a GPIO LOW becomes `True` (pressed). This is explicitly documented in the GPIO Driver API.

---

### ADR-003 — Timing Strategy: Monotonic Elapsed-Time Polling

**Status:** Decided

**Context:** Phase durations must be measured accurately over 8 hours. Options include: hardware timers (via OS POSIX timer APIs), `time.sleep()` for full phase duration, or monotonic elapsed-time polling within a main loop.

**Options Considered:**
1. **`time.sleep()` for full phase duration:** Simple; but suspends the main loop, preventing CRB monitoring during sleep. Violates FR-006.
2. **POSIX `timer_create()` with SIGALRM:** Interrupt-driven; requires signal handling and is fragile in Python due to GIL interactions.
3. **Monotonic elapsed-time polling in main loop:** `time.monotonic()` captured at phase entry; compared each tick. CRB sampled every tick. No sleeping during phases.

**Decision:** Monotonic elapsed-time polling (Option 3).

**Rationale:** Keeps the main loop single-threaded and signal-free, eliminating race conditions. CRB is sampled every tick (FR-006 satisfied). `time.monotonic()` is immune to wall-clock adjustments (NTP, DST), satisfying NF-008. The 10 ms tick provides adequate resolution given the 100 ms YELLOW tolerance (NF-002) and 200 ms PEDESTRIAN WALK tolerance (NF-004).

**Consequences:** Phase timing accuracy is bounded by ±10 ms (one tick). This is well within all stated tolerances. CPU is consumed for the full duration of all phases (no sleep between ticks); at 10 ms ticks, this is negligible on a modern Raspberry Pi.

---

### ADR-004 — LED Series Resistor Value: 270 Ω

**Status:** Decided

**Context:** LEDs require current-limiting resistors when driven from GPIO outputs. The resistor value determines LED brightness and GPIO current draw.

**Options Considered:**
1. **330 Ω:** Common value cited in many Pi tutorials. At 3.3 V GPIO and V_F = 2.0 V: I = (3.3-2.0)/330 = 3.94 mA.
2. **270 Ω:** Next lower E24 standard value. At 3.3 V GPIO and V_F = 2.0 V: I = (3.3-2.0)/270 = 4.81 mA.
3. **220 Ω:** Higher current (5.9 mA), brighter, but closer to 8 mA nominal GPIO drive limit.

**Decision:** 270 Ω (Option 2), with 330 Ω as acceptable alternate.

**Rationale:** 270 Ω yields 4.81 mA, providing visible brightness at 2 m (NF-009) with margin below the 8 mA nominal GPIO drive limit. 330 Ω is also acceptable and slightly more conservative; both values are documented to avoid build ambiguity.

**Consequences:** LED current draw of 4.81 mA per active LED. Only one LED active at a time (FR-005), so total GPIO current is always < 5 mA, well within the 50 mA GPIO bank limit.

---

### ADR-005 — No Operator Reset Button

**Status:** Decided

**Context:** OQ-002 asked whether a second button for operator reset should be added.

**Options Considered:**
1. **Add reset button on GPIO 23 (or next available):** Wiring, debounce logic, state machine handling required. No GPIO pin allocated in SYS-TLC-001.
2. **Power-cycle as reset mechanism:** Power off/on achieves identical effect per NF-007 and Edge Case F.

**Decision:** No reset button (Option 2).

**Rationale:** SYS-TLC-001 does not specify a reset button. The power-cycle reset is fully specified (FR-016, FR-017, NF-007). Adding a reset button without specification risks introducing unspecified behavior (e.g., what happens to CR_PENDING on reset-button press during PEDESTRIAN WALK).

**Consequences:** Operator must power-cycle to reset. This is adequate for a bench prototype.

---

### ADR-006 — CR During PEDESTRIAN WALK: Discard

**Status:** Decided

**Context:** OQ-003 asked whether a CR pressed during PEDESTRIAN WALK should be queued for the next cycle or discarded.

**Options Considered:**
1. **Queue for next cycle:** More realistic traffic controller behavior. Requires additional `cr_queued` flag or counter. Complexity increases.
2. **Discard per FR-012:** Simpler; clearly specified in SYS-TLC-001.

**Decision:** Discard (Option 2), per FR-012.

**Rationale:** FR-012 is unambiguous. FR-013 specifies only one PEDESTRIAN WALK per service cycle. Queuing would require multi-event tracking that contradicts the single-boolean CR_PENDING model and introduces untested behavior. For a future revision, a separate `cr_queued` counter could be added without architectural disruption.

**Consequences:** A pedestrian pressing the CRB during PEDESTRIAN WALK must press again after GREEN illuminates to register their request. This is a known limitation for the bench prototype.

---

## 12. Glossary

| Term | Definition |
|------|------------|
| BCM | Broadcom chip pin numbering scheme used by the Raspberry Pi GPIO header. All GPIO pin references in this document use BCM numbering. |
| CRB | Crosswalk Request Button — the single momentary pushbutton input on GPIO 18. |
| CR | Crosswalk Request — the internal boolean flag (`cr_pending`) indicating a validated pedestrian button press awaiting service. |
| CR_PENDING | The boolean state variable within the State Machine Module that is True when a CR has been registered and not yet serviced. |
| E24 | The E24 standard resistor series, providing 24 values per decade (e.g., 220, 270, 330, 390 Ω). |
| Elapsed-time polling | A timing technique in which a timestamp is captured at event start and compared to the current monotonic time each tick to determine whether a duration has expired. |
| FSM | Finite State Machine. The four-state behavioral model (S1_GREEN, S2_YELLOW, S3_RED, S4_PED) at the core of this system. |
| GPIO | General-Purpose Input/Output. Digital I/O pins on the Raspberry Pi header, configurable as input or output in software. |
| GPIO Driver Layer | The software module (`gpio_driver.py`) that abstracts all RPi.GPIO library calls and provides named functions for pin operations. |
| GIL | Global Interpreter Lock — CPython's mechanism that allows only one thread to execute Python bytecode at a time. Not a concern for this single-threaded design. |
| Lockout | The 300 ms window following a valid CRB press during which further CRB transitions are ignored by the Debounce Module. |
| Monotonic clock | A clock source (`time.monotonic()` in Python) that is guaranteed to never go backward, regardless of wall-clock adjustments. |
| NTP | Network Time Protocol — a protocol for synchronizing system clocks. `time.monotonic()` is unaffected by NTP adjustments. |
| Phase timer | The elapsed-time measurement within the State Machine Module tracking how long the system has been in the current state. |
| Pull-up | A resistor (internal or external) connecting a GPIO input to a positive supply, holding the pin HIGH when no other driver is active. |
| RPi.GPIO | The standard Python library for controlling Raspberry Pi GPIO pins. |
| S1_GREEN | State machine state: GREEN phase active, GPIO 22 HIGH. |
| S2_YELLOW | State machine state: YELLOW phase active, GPIO 27 HIGH. |
| S3_RED | State machine state: RED phase active, GPIO 17 HIGH. |
| S4_PED | State machine state: PEDESTRIAN WALK phase active, GPIO 17 HIGH. |
| S_ERROR | State machine fault state: undefined/unrecognized state. GPIO 17 HIGH, system halted. |
| Stability timer | The 50 ms timer within the Debounce Module that confirms a CRB press has held stable before registering a valid press event. |
| Tick | One iteration of the main control loop. Target period: 10 ms. |
| TLC | Traffic Light Controller — the system specified by SYS-TLC-001 and architected by this document. |
| V_F | Forward voltage of an LED — the voltage drop across the LED when conducting. Typically 1.8–2.2 V for standard red/yellow/green LEDs. |

---

## 13. Traceability Matrix

### 13.1 Functional Requirements → Component

| FR | GPIO Driver | Debounce Module | State Machine | Timing Module | Main Loop |
|----|-------------|-----------------|---------------|---------------|-----------|
| FR-001 | | | X | X | |
| FR-002 | X | | X | | |
| FR-003 | X | | X | | |
| FR-004 | X | | X | | |
| FR-005 | X | | X | | |
| FR-006 | X | X | | | X |
| FR-007 | | X | X | | |
| FR-008 | | | X | | |
| FR-009 | X | | X | | |
| FR-010 | | | X | | |
| FR-011 | | | X | X | |
| FR-012 | | X | X | | |
| FR-013 | | | X | | |
| FR-014 | | | X | | |
| FR-015 | | | X | | |
| FR-016 | | | X | | X |
| FR-017 | X | | | | X |
| FR-018 | | X | | | |
| FR-019 | | X | | X | |
| FR-020 | | X | | X | |

### 13.2 Non-Functional Requirements → Component

| NFR | GPIO Driver | Debounce Module | State Machine | Timing Module | Main Loop | LED Circuit |
|-----|-------------|-----------------|---------------|---------------|-----------|-------------|
| NF-001 | | | | X | | |
| NF-002 | | | | X | | |
| NF-003 | | | | X | | |
| NF-004 | | | | X | | |
| NF-005 | X | | X | X | X | |
| NF-006 | | X | | X | | |
| NF-007 | | | X | | X | |
| NF-008 | | | | X | | |
| NF-009 | X | | | | | X |
| NF-010 | X | | X | | | |

### 13.3 Functional Requirements → Integration Contract

| FR | IC-001 | IC-002 | IC-003 | IC-004 | IC-005 |
|----|--------|--------|--------|--------|--------|
| FR-001 | | | | X | X |
| FR-002 | X | | | X | |
| FR-003 | X | | | X | |
| FR-004 | X | | | X | |
| FR-005 | X | | | X | |
| FR-006 | | X | X | | |
| FR-007 | | X | X | | |
| FR-008 | | | X | X | |
| FR-009 | X | | | X | |
| FR-010 | | | | X | |
| FR-011 | | | | X | X |
| FR-012 | | | X | | |
| FR-013 | | | X | | |
| FR-014 | | | X | | |
| FR-015 | | | X | | |
| FR-016 | X | | | X | |
| FR-017 | X | | | | X |
| FR-018 | | X | X | | |
| FR-019 | | X | X | | X |
| FR-020 | | | X | | X |

### 13.4 Requirements → Test Case

| Requirement | TC-001 | TC-002 | TC-003 | TC-004 | TC-005 | TC-006 | TC-007 | TC-008 | TC-009 | TC-010 | TC-011 | TC-012 | TC-013 |
|-------------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| FR-001 | X | | | | | | | | | | | | |
| FR-002 | X | | | | | | | | | | | | |
| FR-003 | X | | | | | | | | | | | | |
| FR-004 | X | | | | | | | | | | | | |
| FR-005 | X | | | | | | | | | | | | |
| FR-006 | | | | | | | | | | | | | |
| FR-007 | | | X | X | X | | X | X | | | | | |
| FR-008 | | | X | X | X | | X | | | | | | |
| FR-009 | | | X | X | X | X | X | | | | | | |
| FR-010 | | | X | X | X | X | X | | | | | | |
| FR-011 | | | | | X | | | | | | | | |
| FR-012 | | | | | | X | | | | | | | |
| FR-013 | | | | | | | X | | | | | | |
| FR-014 | | | X | | | | | | | | | | |
| FR-015 | | | | X | | | | | | | | | |
| FR-016 | | X | | | | | | | | | X | | |
| FR-017 | | X | | | | | | | | | | | |
| FR-018 | | | | | | | | X | | | | | |
| FR-019 | | | | | | | | X | | | | | |
| FR-020 | | | | | | | | | X | | | | |
| NF-001 | X | | | | | | | | | | | X | |
| NF-002 | X | | | | | | | | | X | | X | |
| NF-003 | X | | | | | | | | | | | X | |
| NF-004 | | | X | X | X | X | X | | | | | X | |
| NF-005 | | | | | | | | | | X | | | |
| NF-006 | | | | | | | | X | | | | | |
| NF-007 | | | | | | | | | | | X | | |
| NF-008 | | | | | | | | | | | | X | |
| C-004 | | | | | | | | | | | | | X |

### 13.5 Integration Contracts → Test Case

| Integration Contract | Test Cases |
|---------------------|-----------|
| IC-001 (GPIO Driver ↔ LED Hardware) | TC-001, TC-002, TC-003, TC-004, TC-005, TC-006, TC-007, TC-010 |
| IC-002 (GPIO Driver ↔ CRB Hardware) | TC-008, TC-009 |
| IC-003 (Debounce ↔ State Machine) | TC-003, TC-004, TC-005, TC-006, TC-007, TC-008, TC-009 |
| IC-004 (State Machine ↔ GPIO Driver) | TC-001, TC-003, TC-004, TC-005, TC-006, TC-007, TC-010, TC-013 |
| IC-005 (Timing Module ↔ All) | TC-001, TC-010, TC-012 |
