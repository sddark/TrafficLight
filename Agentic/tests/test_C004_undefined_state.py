# =============================================================================
# test_C004_undefined_state.py
# Document reference: ARCH-TLC-001
# Requirements covered: C-004
# Description: Verifies undefined/invalid state handling.  Injecting an
#              out-of-range value into current_state must trigger
#              enter_error_state(), illuminate red only (GPIO17 HIGH, others
#              LOW), and raise RuntimeError to terminate the process.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest

from tlc.state_machine import StateMachine, PhaseState
from tests.test_helpers import MockGPIODriver, TICK_MS


def _make_sm() -> tuple[StateMachine, MockGPIODriver]:
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


class TestC004UndefinedStateDetection(unittest.TestCase):
    """C-004: undefined state must cause error state entry and RuntimeError."""

    def test_C004_update_with_invalid_state_calls_enter_error_state(self):
        """
        Forcibly set current_state to 0 (not in PhaseState enum) then call
        update() — the SM must invoke enter_error_state(), which raises
        RuntimeError.
        """
        sm, gpio = _make_sm()
        sm.current_state = 0   # inject invalid state

        with self.assertRaises(RuntimeError,
                               msg="update() must raise RuntimeError for undefined state (C-004)"):
            sm.update(False, TICK_MS)

    def test_C004_runtime_error_message_contains_undefined_state(self):
        """RuntimeError message must reference 'undefined state' (C-004)."""
        sm, gpio = _make_sm()
        sm.current_state = 0

        try:
            sm.update(False, TICK_MS)
            self.fail("Expected RuntimeError was not raised")
        except RuntimeError as exc:
            self.assertIn("undefined state", str(exc).lower(),
                          f"RuntimeError message '{exc}' does not mention "
                          f"'undefined state' (C-004)")

    def test_C004_gpio17_high_after_error_state_entry(self):
        """
        After enter_error_state(), the last gpio_set_leds() call must be
        (red=True, yellow=False, green=False) — only red illuminated.
        """
        sm, gpio = _make_sm()
        sm.current_state = 0

        try:
            sm.update(False, TICK_MS)
        except RuntimeError:
            pass  # expected

        self.assertTrue(len(gpio.led_calls) >= 1,
                        "gpio_set_leds() must have been called during error state")
        red, yellow, green = gpio.led_calls[-1]
        self.assertTrue(red,     "GPIO17 (red) must be HIGH in S_ERROR (C-004)")
        self.assertFalse(yellow, "GPIO27 (yellow) must be LOW in S_ERROR (C-004)")
        self.assertFalse(green,  "GPIO22 (green) must be LOW in S_ERROR (C-004)")

    def test_C004_current_state_set_to_s_error(self):
        """current_state must be S_ERROR after enter_error_state() runs."""
        sm, gpio = _make_sm()
        sm.current_state = 0

        try:
            sm.update(False, TICK_MS)
        except RuntimeError:
            pass

        self.assertEqual(sm.current_state, PhaseState.S_ERROR,
                         "current_state must be S_ERROR after error entry (C-004)")

    def test_C004_cr_pending_cleared_on_error_state_entry(self):
        """cr_pending must be False after enter_error_state()."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)      # latch CR
        self.assertTrue(sm.cr_pending)

        sm.current_state = 0      # inject invalid state
        try:
            sm.update(False, TICK_MS)
        except RuntimeError:
            pass

        self.assertFalse(sm.cr_pending,
                         "cr_pending must be False in S_ERROR (C-004)")

    def test_C004_enter_error_state_raises_runtime_error(self):
        """
        enter_error_state() must raise RuntimeError when called directly.
        This tests the method independently of update().
        """
        sm, gpio = _make_sm()
        with self.assertRaises(RuntimeError):
            sm.enter_error_state()

    def test_C004_enter_error_state_sets_red_only_directly(self):
        """Direct call to enter_error_state() must set (True, False, False)."""
        sm, gpio = _make_sm()
        try:
            sm.enter_error_state()
        except RuntimeError:
            pass
        red, yellow, green = gpio.led_calls[-1]
        self.assertTrue(red)
        self.assertFalse(yellow)
        self.assertFalse(green)

    def test_C004_unknown_integer_state_99_not_in_enum_triggers_error(self):
        """
        S_ERROR has value 99 in the enum, but injecting an *unregistered*
        integer value (e.g., 7) that is not any PhaseState member must also
        trigger the error path.
        """
        sm, gpio = _make_sm()
        sm.current_state = 7   # not a valid PhaseState

        with self.assertRaises(RuntimeError):
            sm.update(False, TICK_MS)

        self.assertEqual(sm.current_state, PhaseState.S_ERROR)

    def test_C004_negative_state_value_triggers_error(self):
        """Negative integers are not valid PhaseState members — must trigger error."""
        sm, gpio = _make_sm()
        sm.current_state = -1

        with self.assertRaises(RuntimeError):
            sm.update(False, TICK_MS)

        red, yellow, green = gpio.led_calls[-1]
        self.assertTrue(red,     "GPIO17 must be HIGH for negative invalid state")
        self.assertFalse(yellow, "GPIO27 must be LOW for negative invalid state")
        self.assertFalse(green,  "GPIO22 must be LOW for negative invalid state")

    def test_C004_runtime_error_propagation_simulates_process_exit(self):
        """
        The RuntimeError raised by enter_error_state() must propagate through
        update() to the caller, enabling main.py to catch it and call sys.exit(1).
        This test confirms the exception is not swallowed inside the SM.
        """
        sm, gpio = _make_sm()
        sm.current_state = 0

        caught = False
        try:
            sm.update(False, TICK_MS)
        except RuntimeError as exc:
            caught = True
            # The error must carry a meaningful message.
            self.assertIsNotNone(str(exc), "RuntimeError must have a message")

        self.assertTrue(caught,
                        "RuntimeError must propagate from update() to caller (C-004)")


if __name__ == "__main__":
    unittest.main()
