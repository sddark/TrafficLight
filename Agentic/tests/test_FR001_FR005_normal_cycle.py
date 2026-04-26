# =============================================================================
# test_FR001_FR005_normal_cycle.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-001, FR-002, FR-003, FR-004, FR-005
# Description: Verifies the normal GREEN→YELLOW→RED→GREEN cycling sequence,
#              correct GPIO mapping per phase, and the invariant that exactly
#              one LED is HIGH in every steady state.
# =============================================================================

# test_helpers must be imported first — it stubs RPi.GPIO before any tlc import.
import tests.test_helpers as helpers  # noqa: F401 (side-effect import)

import unittest
from unittest.mock import patch

from tlc.state_machine import StateMachine, PhaseState
from tests.test_helpers import (
    MockGPIODriver,
    DURATION_GREEN_MS,
    DURATION_YELLOW_MS,
    DURATION_RED_MS,
    TICK_MS,
    ticks_for_ms,
)

PIN_RED    = 17
PIN_YELLOW = 27
PIN_GREEN  = 22


def _make_sm() -> tuple["StateMachine", MockGPIODriver]:
    """Return a freshly initialised (StateMachine, MockGPIODriver) pair."""
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


def _advance_to_next_transition(sm, start_ms: float, duration_ms: float,
                                 press_ticks: set | None = None) -> float:
    """
    Advance the SM by enough ticks to exit the current phase.
    Returns the tick_time_ms of the tick that triggered the transition.
    """
    if press_ticks is None:
        press_ticks = set()
    n = ticks_for_ms(duration_ms)
    for i in range(n + 2):          # +2 gives a margin tick
        t = start_ms + i * TICK_MS
        vp = i in press_ticks
        sm.update(vp, t)
        if i >= n - 1:              # could have transitioned by now
            return t
    return start_ms + (n + 1) * TICK_MS


class TestFR001StateOrder(unittest.TestCase):
    """FR-001: system cycles GREEN→YELLOW→RED→GREEN continuously."""

    def test_FR001_green_to_yellow_transition(self):
        """After DURATION_GREEN_MS elapses the state must become S2_YELLOW."""
        sm, gpio = _make_sm()
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN)

        n_green = ticks_for_ms(DURATION_GREEN_MS)
        t = 0.0
        final_state = PhaseState.S1_GREEN
        for i in range(n_green + 5):
            t = i * TICK_MS
            final_state = sm.update(False, t)
            if final_state == PhaseState.S2_YELLOW:
                break

        self.assertEqual(final_state, PhaseState.S2_YELLOW,
                         "State did not advance to S2_YELLOW after GREEN duration")

    def test_FR001_yellow_to_red_transition(self):
        """After GREEN+YELLOW the state must become S3_RED."""
        sm, gpio = _make_sm()
        n = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS)
        state = PhaseState.S1_GREEN
        for i in range(n + 10):
            state = sm.update(False, i * TICK_MS)
        self.assertEqual(state, PhaseState.S3_RED)

    def test_FR001_red_to_green_transition_no_cr(self):
        """After one full cycle without CR the state returns to S1_GREEN."""
        sm, gpio = _make_sm()
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(total_ms)
        state = PhaseState.S1_GREEN
        for i in range(n + 10):
            state = sm.update(False, i * TICK_MS)
        self.assertEqual(state, PhaseState.S1_GREEN,
                         "State did not return to S1_GREEN after full cycle")

    def test_FR001_two_full_cycles_complete(self):
        """FR-001: at least 2 full cycles run correctly without CR."""
        sm, gpio = _make_sm()
        cycle_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        two_cycle_ms = 2 * cycle_ms
        n = ticks_for_ms(two_cycle_ms)

        # Track how many times we visit each state.
        visits = {PhaseState.S1_GREEN: 0,
                  PhaseState.S2_YELLOW: 0,
                  PhaseState.S3_RED: 0}
        prev = None
        for i in range(n + 20):
            s = sm.update(False, i * TICK_MS)
            if s != prev:
                if s in visits:
                    visits[s] += 1
                prev = s

        # First S1_GREEN counts startup entry; we expect >=2 entries for S2 and S3.
        self.assertGreaterEqual(visits[PhaseState.S2_YELLOW], 2,
                                "YELLOW entered fewer than 2 times over two cycles")
        self.assertGreaterEqual(visits[PhaseState.S3_RED], 2,
                                "RED entered fewer than 2 times over two cycles")


class TestFR005ExactlyOneLEDActive(unittest.TestCase):
    """FR-005: exactly one LED is HIGH at all times in steady state."""

    def _assert_exactly_one_high(self, led_calls, label):
        for call_args in led_calls:
            red, yellow, green = call_args
            active = sum([red, yellow, green])
            self.assertEqual(active, 1,
                             f"{label}: expected exactly 1 LED HIGH, got "
                             f"red={red} yellow={yellow} green={green}")

    def test_FR005_exactly_one_led_per_transition_in_full_cycle(self):
        """Every gpio_set_leds() call during a no-CR cycle has exactly one True."""
        sm, gpio = _make_sm()
        cycle_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(cycle_ms) + 20
        for i in range(n):
            sm.update(False, i * TICK_MS)
        # initialize() makes first call; update() makes subsequent calls on transitions.
        self._assert_exactly_one_high(gpio.led_calls, "normal cycle")

    def test_FR005_no_simultaneous_leds_across_two_cycles(self):
        """Two full cycles produce no simultaneous multi-LED activations."""
        sm, gpio = _make_sm()
        cycle_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(2 * cycle_ms) + 20
        for i in range(n):
            sm.update(False, i * TICK_MS)
        self._assert_exactly_one_high(gpio.led_calls, "two-cycle")


class TestFR002GpioMapping(unittest.TestCase):
    """FR-002: During GREEN, GPIO22 HIGH; GPIO17 LOW; GPIO27 LOW."""

    def test_FR002_green_phase_gpio_state(self):
        """initialize() must set green=True, red=False, yellow=False."""
        sm, gpio = _make_sm()
        # initialize() is the first gpio_set_leds call.
        first_call = gpio.led_calls[0]
        red, yellow, green = first_call
        self.assertTrue(green,   "GPIO22 (green) must be HIGH during S1_GREEN")
        self.assertFalse(red,    "GPIO17 (red) must be LOW during S1_GREEN")
        self.assertFalse(yellow, "GPIO27 (yellow) must be LOW during S1_GREEN")

    def test_FR002_green_gpio_after_second_cycle_entry(self):
        """GPIO22 goes HIGH again when re-entering GREEN after one full cycle."""
        sm, gpio = _make_sm()
        cycle_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(cycle_ms) + 20
        for i in range(n):
            sm.update(False, i * TICK_MS)
        # Last call should be the re-entry into GREEN.
        red, yellow, green = gpio.led_calls[-1]
        self.assertTrue(green,   "Re-entry to GREEN must set GPIO22 HIGH")
        self.assertFalse(red,    "Re-entry to GREEN must keep GPIO17 LOW")
        self.assertFalse(yellow, "Re-entry to GREEN must keep GPIO27 LOW")


class TestFR003GpioMapping(unittest.TestCase):
    """FR-003: During YELLOW, GPIO27 HIGH; GPIO17 LOW; GPIO22 LOW."""

    def test_FR003_yellow_phase_gpio_state(self):
        """On transition to S2_YELLOW, gpio_set_leds(False, True, False) called."""
        sm, gpio = _make_sm()
        n = ticks_for_ms(DURATION_GREEN_MS) + 10
        prev = PhaseState.S1_GREEN
        yellow_call = None
        for i in range(n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S2_YELLOW and prev == PhaseState.S1_GREEN:
                yellow_call = gpio.led_calls[-1]
                break
            prev = s
        self.assertIsNotNone(yellow_call, "Never transitioned to S2_YELLOW")
        red, yellow, green = yellow_call
        self.assertTrue(yellow,  "GPIO27 (yellow) must be HIGH in S2_YELLOW")
        self.assertFalse(red,    "GPIO17 (red) must be LOW in S2_YELLOW")
        self.assertFalse(green,  "GPIO22 (green) must be LOW in S2_YELLOW")


class TestFR004GpioMapping(unittest.TestCase):
    """FR-004: During RED, GPIO17 HIGH; GPIO27 LOW; GPIO22 LOW."""

    def test_FR004_red_phase_gpio_state(self):
        """On transition to S3_RED, gpio_set_leds(True, False, False) called."""
        sm, gpio = _make_sm()
        n = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 20
        prev = None
        red_call = None
        for i in range(n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S3_RED and prev != PhaseState.S3_RED:
                red_call = gpio.led_calls[-1]
                break
            prev = s
        self.assertIsNotNone(red_call, "Never transitioned to S3_RED")
        red, yellow, green = red_call
        self.assertTrue(red,     "GPIO17 (red) must be HIGH in S3_RED")
        self.assertFalse(yellow, "GPIO27 (yellow) must be LOW in S3_RED")
        self.assertFalse(green,  "GPIO22 (green) must be LOW in S3_RED")


if __name__ == "__main__":
    unittest.main()
