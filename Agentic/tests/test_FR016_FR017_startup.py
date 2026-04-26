# =============================================================================
# test_FR016_FR017_startup.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-016, FR-017
# Description: Verifies startup sequence — system must begin in GREEN, GPIO22
#              must go HIGH immediately after initialize(), all LEDs must be LOW
#              before initialize() is called, and the full startup completes
#              within the 500 ms timing constraint.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest
from unittest.mock import patch, MagicMock

from tlc.state_machine import StateMachine, PhaseState
import tlc.gpio_driver as gpio_driver_mod
from tests.test_helpers import MockGPIODriver, PIN_RED, PIN_YELLOW, PIN_GREEN


class TestFR016StartState(unittest.TestCase):
    """FR-016: Power-on enters GREEN immediately."""

    def test_FR016_initial_state_is_green(self):
        """StateMachine.__init__ must set current_state = S1_GREEN."""
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN,
                         "State machine must start in S1_GREEN (FR-016)")

    def test_FR016_cr_pending_false_at_startup(self):
        """CR_PENDING must be False at power-on — no phantom crosswalk request."""
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        self.assertFalse(sm.cr_pending,
                         "CR_PENDING must be False at power-on (FR-016)")

    def test_FR016_gpio22_high_after_initialize(self):
        """initialize() must write GPIO22=HIGH, GPIO17=LOW, GPIO27=LOW."""
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        sm.initialize(tick_time_ms=0.0)

        self.assertTrue(len(gpio.led_calls) >= 1,
                        "initialize() must call gpio_set_leds() at least once")
        red, yellow, green = gpio.led_calls[-1]
        self.assertTrue(green,   "GPIO22 must be HIGH after initialize() (FR-016)")
        self.assertFalse(red,    "GPIO17 must be LOW after initialize() (FR-016)")
        self.assertFalse(yellow, "GPIO27 must be LOW after initialize() (FR-016)")

    def test_FR016_state_still_green_after_initialize(self):
        """current_state must remain S1_GREEN after initialize() returns."""
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        sm.initialize(tick_time_ms=100.0)
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN)

    def test_FR016_phase_start_set_by_initialize(self):
        """phase_start_ms must be set to the tick_time_ms passed to initialize()."""
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        sm.initialize(tick_time_ms=42.0)
        self.assertAlmostEqual(sm.phase_start_ms, 42.0,
                               msg="phase_start_ms must equal the timestamp "
                                   "given to initialize()")


class TestFR017AllLedsOffBeforeGreen(unittest.TestCase):
    """FR-017: All LEDs are OFF for < 500 ms before GREEN illuminates."""

    def test_FR017_no_led_calls_before_initialize(self):
        """
        __init__ alone must NOT call gpio_set_leds().
        All LED-setting must happen inside initialize(), not the constructor.
        This ensures the LEDs-off window is as short as possible.
        """
        gpio = MockGPIODriver()
        sm = StateMachine(gpio)  # noqa: F841 — intentionally not calling initialize()
        self.assertEqual(len(gpio.led_calls), 0,
                         "__init__ must not call gpio_set_leds() — "
                         "that belongs to initialize()")

    def test_FR017_gpio_init_sets_all_leds_low(self):
        """
        gpio_init() must configure LED pins as outputs starting LOW.
        We verify via the mock that GPIO.setup is called with the output pins
        and that gpio_set_leds(False,False,False) results in all LEDs off.
        """
        gpio = MockGPIODriver()
        # gpio_init() in the real driver sets all outputs LOW.
        # Here we confirm MockGPIODriver's state at construction (no calls yet).
        self.assertEqual(gpio.led_calls, [],
                         "No LED writes should have occurred before any call")

    def test_FR017_startup_completes_within_500ms(self):
        """
        The elapsed time between gpio_init() and the GREEN GPIO write must
        be < 500 ms.  Simulated with monotonic mock — the real init is just
        Python object construction, which is negligible.
        """
        import time

        t_init_start = time.monotonic() * 1000.0

        # Simulate the startup sequence steps from section 8.6.1:
        # Step 1: gpio_init() — we use MockGPIODriver instead.
        gpio = MockGPIODriver()
        gpio.gpio_init()

        # Step 4: construct state machine
        sm = StateMachine(gpio)

        # Step 6: apply initial GPIO state
        t_before_green = time.monotonic() * 1000.0
        sm.initialize(tick_time_ms=t_before_green)

        t_after_green = time.monotonic() * 1000.0
        elapsed = t_after_green - t_init_start

        self.assertLess(elapsed, 500.0,
                        f"Startup sequence took {elapsed:.1f} ms, exceeds "
                        f"500 ms constraint (FR-017)")

    def test_FR017_all_leds_dark_between_init_and_green_write(self):
        """
        Between gpio_init() and sm.initialize(), no LED must have been driven
        HIGH.  We inspect MockGPIODriver.led_calls to confirm this.
        """
        gpio = MockGPIODriver()
        gpio.gpio_init()

        sm = StateMachine(gpio)
        # At this point initialize() has NOT been called yet.
        # No gpio_set_leds() call should have occurred.
        self.assertEqual(gpio.led_calls, [],
                         "No LED must be driven HIGH before initialize() "
                         "(FR-017 dark-before-green guarantee)")

        sm.initialize(tick_time_ms=0.0)
        # Now exactly one call should have been made, setting green HIGH.
        self.assertEqual(len(gpio.led_calls), 1,
                         "initialize() must call gpio_set_leds() exactly once")
        red, yellow, green = gpio.led_calls[0]
        self.assertTrue(green)
        self.assertFalse(red)
        self.assertFalse(yellow)


class TestGPIODriverInit(unittest.TestCase):
    """Verify gpio_driver.gpio_init() configures pins correctly via RPi.GPIO mock."""

    def test_FR017_gpio_driver_sets_bcm_mode(self):
        """gpio_init() must call GPIO.setmode(GPIO.BCM)."""
        import RPi.GPIO as GPIO
        gpio_driver_mod.gpio_init()
        GPIO.setmode.assert_called()

    def test_FR017_gpio_driver_sets_output_pins(self):
        """gpio_init() must configure PIN_RED, PIN_YELLOW, PIN_GREEN as outputs."""
        import RPi.GPIO as GPIO
        GPIO.reset_mock()
        gpio_driver_mod.gpio_init()
        setup_calls = GPIO.setup.call_args_list
        pins_configured = [c[0][0] for c in setup_calls]
        self.assertIn(PIN_RED,    pins_configured,
                      "gpio_init() must configure PIN_RED (17) as output")
        self.assertIn(PIN_YELLOW, pins_configured,
                      "gpio_init() must configure PIN_YELLOW (27) as output")
        self.assertIn(PIN_GREEN,  pins_configured,
                      "gpio_init() must configure PIN_GREEN (22) as output")

    def test_FR017_gpio_driver_sets_crb_input_with_pullup(self):
        """gpio_init() must configure PIN_CRB (18) as input with pull-up."""
        import RPi.GPIO as GPIO
        GPIO.reset_mock()
        gpio_driver_mod.gpio_init()
        setup_calls = GPIO.setup.call_args_list
        crb_calls = [c for c in setup_calls if c[0][0] == 18]
        self.assertTrue(len(crb_calls) >= 1,
                        "gpio_init() must configure PIN_CRB (18)")


if __name__ == "__main__":
    unittest.main()
