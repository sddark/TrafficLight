---
name: Domain Patterns: Embedded GPIO / Raspberry Pi Systems
description: Recurring patterns, preferred resolutions, and common failure modes for Raspberry Pi GPIO system architecture engagements
type: reference
---

## LED Drive Circuit
- Raspberry Pi GPIO outputs: 3.3 V logic, 8 mA nominal / 16 mA max per pin, 50 mA max total GPIO bank.
- Standard LED series resistor formula: R = (V_GPIO - V_F) / I_target. Typical: (3.3 - 2.0) / 0.005 = 260 Ω → use 270 Ω (E24). 330 Ω is a safe alternate.
- V_F range: 1.8–2.2 V red/yellow, 2.0–2.4 V green. Size resistor for worst case (lowest V_F = highest current).
- Only one LED on at a time keeps total GPIO current well within limits.

## Button / CRB Input
- Prefer active-low + internal pull-up (~50 kΩ on Pi) over active-high + external pull-down.
- Rationale: disconnected wire fails safe (reads HIGH = released, no spurious press).
- Contact bounce assumption: ≤ 20 ms for standard tactile buttons (ALPS SKHHAPA010 class).
- Debounce architecture: two-stage — (1) 50 ms stability timer, (2) 300 ms post-press lockout. This pattern satisfies most embedded button specs.

## Timing Strategy
- For prototypes with tolerances ≥ 100 ms: monotonic elapsed-time polling in a 10 ms main loop is sufficient and avoids signal/timer complexity.
- Use `time.monotonic()` in Python — immune to NTP/wall-clock adjustment, sub-ms resolution on Linux.
- `time.sleep()` for full phase durations violates continuous-monitoring requirements (e.g., button sampling FR-006 pattern). Always use polling loops.
- 10 ms tick period → worst-case transition latency < 20 ms (tick overshoot + GPIO write). Satisfies 50 ms NF budgets with 30 ms margin.
- Drift over 8 hours: CLOCK_MONOTONIC disciplined by kernel NTP loop → < 1 ms/hr → 8 ms/8 hr. Negligible vs. 100 ms timing tolerances.

## State Machine Encoding
- Use Python IntEnum for states: enables arithmetic comparison, clear names, and catching undefined-state values.
- Phase timer: store `phase_start_ms` (monotonic float) at state entry. Compute elapsed each tick. Never accumulate time increments — avoids drift.
- Error/undefined state (C-004 pattern): if state not in known set, illuminate red only and raise RuntimeError to halt. OS retains GPIO state after process exit.

## Single-Threaded Polling Loop Pattern
- Main loop: sample inputs → debounce → state machine update (which writes GPIO if transition) → sleep remainder.
- All modules called with the same `tick_start_ms` captured at top of loop — prevents inconsistent elapsed-time reads within a tick.
- Do NOT re-read GPIO within a tick after the initial sample; pass the captured value through.

## Common Integration Failure Modes
- Forgetting to invert active-low button reading before passing to debounce (raw GPIO LOW must become True = pressed in API).
- Writing GPIO outputs on every tick instead of only on transition — causes unnecessary bus traffic and potential glitches.
- Using `time.sleep(phase_duration)` for phase timing — prevents button monitoring during phase.
- Resetting phase_start_ms with `now_ms()` called late in the tick instead of at tick_start — introduces one-tick error in phase duration measurement.
- Not handling the case where `valid_press_event=True` and `CR_PENDING=True` simultaneously (second press must be silently discarded, not re-latched or logged as error).
