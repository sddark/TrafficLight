# =============================================================================
# tlc/gpio_driver.py
# Document reference: ARCH-TLC-001
#
# Responsibilities:
#   - Configure Raspberry Pi GPIO pins for the Traffic Light Controller (TLC).
#   - Drive the three LED outputs (RED, YELLOW, GREEN) as BCM digital outputs.
#   - Read the Crosswalk Request Button (CRB) input with active-low logic.
#   - Provide a safe cleanup routine to de-energise all outputs on exit.
#
# Assumptions and constraints:
#   - RPi.GPIO is available at import time (or stubbed in sys.modules by tests).
#   - Pin numbers use BCM numbering (ADR-001).
#   - CRB is active-low with internal pull-up (IC-002, ADR-002).
#   - Caller ensures at most one LED argument is True per gpio_set_leds() call
#     (FR-005); this module does NOT enforce that invariant itself.
# =============================================================================

import RPi.GPIO as GPIO

# BCM pin assignments — FR-002, FR-003, FR-004, IC-002
PIN_RED    = 17   # BCM; FR-004: GPIO17 drives the RED LED
PIN_YELLOW = 27   # BCM; FR-003: GPIO27 drives the YELLOW LED
PIN_GREEN  = 22   # BCM; FR-002: GPIO22 drives the GREEN LED
PIN_CRB    = 18   # BCM; IC-002: active-low CRB input with internal pull-up


def gpio_init() -> None:
    """
    Initialise all GPIO pins for TLC operation.

    Configures LED pins as outputs (all starting LOW) and CRB as an input with
    the internal pull-up resistor enabled.  All LEDs are de-energised before
    the GREEN phase illuminates, satisfying the FR-017 dark-window requirement.

    Sets up hardware debounce on PIN_CRB with bouncetime=50 (FR-019) so that
    signal transients shorter than 50 ms are automatically rejected by RPi.GPIO.
    """
    # FR-017: all LEDs off (LOW) before GREEN illuminates
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_RED,    GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_YELLOW, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_GREEN,  GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_CRB,    GPIO.IN,  pull_up_down=GPIO.PUD_UP)  # ADR-002: pull-up for active-low

    # FR-019: hardware debounce — bouncetime=50 ms filters transients shorter than 50 ms
    # GPIO.FALLING means activation (GPIO LOW in active-low circuit)
    GPIO.add_event_detect(PIN_CRB, GPIO.FALLING, bouncetime=50)


def gpio_cleanup() -> None:
    """
    De-energise all LED outputs and release GPIO resources.

    Called on normal exit and on RuntimeError (C-004 fault path) via the
    finally block in main.py to comply with NF-007 (safe shutdown).
    """
    GPIO.output(PIN_RED,    GPIO.LOW)
    GPIO.output(PIN_YELLOW, GPIO.LOW)
    GPIO.output(PIN_GREEN,  GPIO.LOW)
    GPIO.cleanup()


def gpio_set_leds(red: bool, yellow: bool, green: bool) -> None:
    """
    Drive the three LED outputs to the requested states.

    Args:
        red:    True → GPIO17 HIGH (LED ON); False → LOW.
        yellow: True → GPIO27 HIGH (LED ON); False → LOW.
        green:  True → GPIO22 HIGH (LED ON); False → LOW.

    Note:
        FR-005: caller is responsible for ensuring at most one argument is True.
        Outputs are written in fixed order (RED, YELLOW, GREEN) per IC-001 to
        produce a deterministic signal sequence observable on a logic analyser.
    """
    # IC-001: fixed write order — RED first, YELLOW second, GREEN third
    GPIO.output(PIN_RED,    GPIO.HIGH if red    else GPIO.LOW)
    GPIO.output(PIN_YELLOW, GPIO.HIGH if yellow else GPIO.LOW)
    GPIO.output(PIN_GREEN,  GPIO.HIGH if green  else GPIO.LOW)


def gpio_read_crb() -> bool:
    """
    Read the Crosswalk Request Button and return True when pressed.

    Returns:
        True if the button is currently pressed (GPIO LOW → active-low logic).
        False if the button is released (GPIO HIGH → internal pull-up).

    Note:
        IC-002: the CRB circuit is active-low.  GPIO.LOW means button pressed.
    """
    # IC-002: active-low — GPIO LOW means button pressed
    return GPIO.input(PIN_CRB) == GPIO.LOW
