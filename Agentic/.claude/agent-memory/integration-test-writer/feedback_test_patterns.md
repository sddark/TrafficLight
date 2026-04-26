---
name: TLC Test Framework Patterns and Conventions
description: Patterns discovered and validated while writing the TLC integration test suite
type: feedback
---

Mock RPi.GPIO before all tlc imports by installing stubs in sys.modules inside test_helpers.py. Every test file imports test_helpers first as a side-effect import to guarantee the stubs are present.

**Why:** RPi module does not exist on Windows/dev machines. Patching sys.modules before any `import tlc.*` prevents ImportError on non-Pi hardware.

**How to apply:** Always place `import tests.test_helpers as helpers  # noqa: F401` as the first import in every test file that touches any tlc module.

---

MockGPIODriver is a plain Python class (no MagicMock inheritance) that records gpio_set_leds() calls in a list. StateMachine accepts any object with a gpio_set_leds() method — use MockGPIODriver, not the real gpio_driver module, in SM tests.

**Why:** StateMachine takes a gpio object (duck-typed), so we pass MockGPIODriver and inspect its led_calls list for precise assertions on GPIO state.

**How to apply:** Pattern `gpio = MockGPIODriver(); sm = StateMachine(gpio); sm.initialize(0.0)` is the standard SM setup fixture in all SM-level tests.

---

Drive the state machine with absolute tick_time_ms values (i * TICK_MS from tick 0), not relative delta. The SM internally computes elapsed_ms(phase_start_ms), so the absolute time must be monotonically increasing and coherent with phase_start_ms set by initialize().

**Why:** If tick_time_ms is not monotonically non-decreasing, the elapsed_ms comparison inside the SM produces incorrect results.

**How to apply:** Always compute t = i * TICK_MS inside test loops. Never reset t between phases.

---

Phase duration measurement: count the number of consecutive ticks the SM stays in a state, then multiply by TICK_MS. One-tick overhead (TICK_MS = 10 ms) is inherent in the polling design and is within all stated tolerances.

**Why:** The SM transitions on the first tick where elapsed >= DURATION_*_MS, so the measured tick count is ceil(DURATION/TICK_MS), giving at most one tick of overshoot.

---

Use ticks_for_ms(duration) + small buffer (5-15 ticks) when advancing past a phase to guarantee the transition has fired before assertions. The buffer handles rounding and the one-tick overhead.
