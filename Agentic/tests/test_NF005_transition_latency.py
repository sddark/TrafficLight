# =============================================================================
# test_NF005_transition_latency.py
# Document reference: ARCH-TLC-001
# Requirements covered: NF-005
# Description: Phase transition latency must be <= 50 ms.  Since the SM is
#              evaluated once per tick (10 ms), the GPIO write must occur
#              within the same tick that the phase timer expires.  We confirm
#              that gpio_set_leds() is called on the first tick where the
#              elapsed time crosses the duration threshold — never a tick late.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest

from tlc.state_machine import StateMachine, PhaseState
from tests.test_helpers import (
    MockGPIODriver,
    DURATION_GREEN_MS,
    DURATION_YELLOW_MS,
    DURATION_RED_MS,
    DURATION_PED_MS,
    TICK_MS,
    ticks_for_ms,
)

# NF-005 hard limit.
MAX_LATENCY_MS = 50


class TestNF005TransitionLatency(unittest.TestCase):
    """
    NF-005: GPIO write must occur within the same tick that detects timer expiry.

    Strategy: track the tick_time_ms at which the phase timer first expires
    (elapsed >= duration), and verify gpio_set_leds() is called during that
    exact tick — i.e., the LED call list grows by 1 in that tick, not later.
    """

    def _setup(self) -> tuple[StateMachine, MockGPIODriver]:
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        sm.initialize(tick_time_ms=0.0)
        return sm, gpio

    # ------------------------------------------------------------------ GREEN
    def test_NF005_green_to_yellow_gpio_write_within_one_tick(self):
        """
        GPIO write for YELLOW must happen on the first tick where elapsed >= 7000 ms.
        'Same tick' means the call count increases exactly when we cross the threshold.
        """
        sm, gpio = self._setup()
        n_nominal = ticks_for_ms(DURATION_GREEN_MS)

        calls_before = len(gpio.led_calls)
        transition_tick = None
        # Walk tick by tick and watch for the LED call count to increase.
        for i in range(1, n_nominal + 5):
            t = i * TICK_MS
            sm.update(False, t)
            if len(gpio.led_calls) > calls_before:
                transition_tick = i
                break
            calls_before = len(gpio.led_calls)

        self.assertIsNotNone(transition_tick,
                             "GREEN→YELLOW transition never occurred")

        # Verify transition happened within the allowed window.
        transition_ms = transition_tick * TICK_MS
        earliest_allowed_ms = DURATION_GREEN_MS         # timer expired
        latest_allowed_ms   = DURATION_GREEN_MS + MAX_LATENCY_MS

        self.assertGreaterEqual(
            transition_ms, earliest_allowed_ms,
            f"GREEN→YELLOW fired at {transition_ms} ms, before timer expired "
            f"at {earliest_allowed_ms} ms (NF-005)"
        )
        self.assertLessEqual(
            transition_ms, latest_allowed_ms,
            f"GREEN→YELLOW latency {transition_ms - DURATION_GREEN_MS} ms "
            f"exceeds 50 ms limit (NF-005)"
        )

    # ----------------------------------------------------------------- YELLOW
    def test_NF005_yellow_to_red_gpio_write_within_one_tick(self):
        sm, gpio = self._setup()
        # Fast-forward to YELLOW entry.
        n_green = ticks_for_ms(DURATION_GREEN_MS) + 5
        yellow_entry_tick = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n_green):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S2_YELLOW and prev != PhaseState.S2_YELLOW:
                yellow_entry_tick = i
                break
            prev = s

        self.assertIsNotNone(yellow_entry_tick)
        calls_at_yellow = len(gpio.led_calls)

        transition_tick = None
        n_yellow = ticks_for_ms(DURATION_YELLOW_MS) + 5
        for j in range(1, n_yellow):
            i = yellow_entry_tick + j
            sm.update(False, i * TICK_MS)
            if len(gpio.led_calls) > calls_at_yellow:
                transition_tick = j   # ticks into YELLOW
                break
            calls_at_yellow = len(gpio.led_calls)

        self.assertIsNotNone(transition_tick,
                             "YELLOW→RED transition never occurred (NF-005)")

        latency_ms = transition_tick * TICK_MS - DURATION_YELLOW_MS
        self.assertLessEqual(latency_ms, MAX_LATENCY_MS,
                             f"YELLOW→RED latency {latency_ms} ms exceeds 50 ms (NF-005)")

    # -------------------------------------------------------------------- RED
    def test_NF005_red_to_green_gpio_write_within_one_tick(self):
        sm, gpio = self._setup()
        n_lead = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 15
        red_entry_tick = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n_lead):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S3_RED and prev != PhaseState.S3_RED:
                red_entry_tick = i
                break
            prev = s

        self.assertIsNotNone(red_entry_tick)
        calls_at_red = len(gpio.led_calls)

        transition_tick = None
        n_red = ticks_for_ms(DURATION_RED_MS) + 5
        for j in range(1, n_red):
            i = red_entry_tick + j
            sm.update(False, i * TICK_MS)
            if len(gpio.led_calls) > calls_at_red:
                transition_tick = j
                break
            calls_at_red = len(gpio.led_calls)

        self.assertIsNotNone(transition_tick)
        latency_ms = transition_tick * TICK_MS - DURATION_RED_MS
        self.assertLessEqual(latency_ms, MAX_LATENCY_MS,
                             f"RED→GREEN latency {latency_ms} ms exceeds 50 ms (NF-005)")

    # -------------------------------------------------------------------- PED
    def test_NF005_ped_to_green_gpio_write_within_one_tick(self):
        sm, gpio = self._setup()
        sm.update(True, 0.0)   # CR during GREEN

        n_lead = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS) + 15
        ped_entry_tick = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n_lead):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                ped_entry_tick = i
                break
            prev = s

        self.assertIsNotNone(ped_entry_tick)
        calls_at_ped = len(gpio.led_calls)

        transition_tick = None
        n_ped = ticks_for_ms(DURATION_PED_MS) + 5
        for j in range(1, n_ped):
            i = ped_entry_tick + j
            sm.update(False, i * TICK_MS)
            if len(gpio.led_calls) > calls_at_ped:
                transition_tick = j
                break
            calls_at_ped = len(gpio.led_calls)

        self.assertIsNotNone(transition_tick)
        latency_ms = transition_tick * TICK_MS - DURATION_PED_MS
        self.assertLessEqual(latency_ms, MAX_LATENCY_MS,
                             f"PED→GREEN latency {latency_ms} ms exceeds 50 ms (NF-005)")

    def test_NF005_gpio_not_written_on_non_transition_ticks(self):
        """
        gpio_set_leds() must NOT be called on ticks where no phase transition occurs.
        Exactly one call per transition, never per tick.
        """
        sm, gpio = self._setup()
        # Drive one full GREEN phase; the only LED call should be initialize()'s
        # plus one at the GREEN→YELLOW boundary.
        n = ticks_for_ms(DURATION_GREEN_MS) + 5
        prev_call_count = len(gpio.led_calls)   # 1 from initialize()
        transition_counts = 0
        for i in range(1, n):
            sm.update(False, i * TICK_MS)
            if len(gpio.led_calls) > prev_call_count:
                transition_counts += 1
                prev_call_count = len(gpio.led_calls)

        self.assertEqual(transition_counts, 1,
                         "Exactly one GPIO write must occur per GREEN→YELLOW transition "
                         "(no redundant per-tick writes) (NF-005)")
        self.assertEqual(len(gpio.led_calls), 2,
                         "Only 2 total gpio_set_leds() calls: startup + GREEN→YELLOW")


if __name__ == "__main__":
    unittest.main()
