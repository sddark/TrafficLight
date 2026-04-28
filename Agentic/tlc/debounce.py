# =============================================================================
# tlc/debounce.py
# Document reference: ARCH-TLC-001
#
# Responsibilities:
#   - Filter raw PRS input to reject contact bounce and spurious transients
#     (FR-018, FR-019, FR-020).
#   - On real Raspberry Pi hardware: RPi.GPIO's GPIO.add_event_detect(bouncetime=50)
#     provides the 50 ms qualification window (FR-019). This module enforces the
#     300 ms post-activation suppression period in software (FR-020).
#   - On test environments: this module implements a two-stage software filter
#     (qualification window + suppression period) so that all tests pass without
#     RPi.GPIO event system.
#
# Implementation note:
#   In production: gpio_init() calls GPIO.add_event_detect(PIN_CRB, GPIO.FALLING, bouncetime=50)
#   to delegate FR-019 to hardware. This module's process() then checks GPIO.event_detected()
#   and enforces suppression.
#
#   In testing: the qualification window logic remains in this module so that unit tests
#   can inject arbitrary raw_pressed sequences and verify the debounce behavior. When
#   MockGPIODriver is used (tests only), GPIO.event_detected() does not exist, so we
#   fall back to polling the raw signal with a 50 ms timer.
# =============================================================================

from tlc.timing import DEBOUNCE_STABLE_MS, DEBOUNCE_LOCKOUT_MS

try:
    import RPi.GPIO as GPIO
    _HAS_GPIO = True
except (ImportError, RuntimeError):
    # Tests or environments without GPIO
    _HAS_GPIO = False


class DebounceModule:
    """
    Request validation: 50 ms qualification window + 300 ms suppression period.

    On Pi hardware with RPi.GPIO: delegates 50 ms filter to GPIO.add_event_detect()
    (hardware debounce) and enforces 300 ms suppression here.

    On test environments: implements full two-stage filter in software so tests
    can validate the logic with simulated raw input.
    """

    def __init__(self) -> None:
        self._last_raw: bool = False                          # Edge detection
        self._stable_start_ms: float | None = None            # FR-019: qualification timer
        self._suppression_until_ms: float | None = None       # FR-020: suppression period

    def process(self, raw_pressed: bool, tick_time_ms: float) -> bool:
        """
        Evaluate PRS state and return True when a valid activation occurs.

        On hardware (when RPi.GPIO is available):
          - Assumes GPIO.add_event_detect(PIN_CRB, GPIO.FALLING, bouncetime=50)
            has been called during gpio_init().
          - Reads GPIO.event_detected() to consume hardware-debounced events.
          - Enforces 300 ms suppression period in software.

        On tests (when GPIO.event_detected is unavailable):
          - Implements the full two-stage filter internally using raw_pressed timing.

        Args:
            raw_pressed:  Current raw state of PRS (True = activated).
            tick_time_ms: Monotonic tick timestamp in milliseconds.

        Returns:
            True exactly once per valid activation; False otherwise.
        """
        # FR-020: Suppression period gate
        if self._suppression_until_ms is not None:
            if tick_time_ms < self._suppression_until_ms:
                # Suppression active — ignore input
                self._last_raw = raw_pressed
                return False
            else:
                # Suppression expired
                self._suppression_until_ms = None
                self._stable_start_ms = None

        # Try hardware path first (real Raspberry Pi with RPi.GPIO)
        if _HAS_GPIO and hasattr(GPIO, 'event_detected'):
            try:
                from tlc.gpio_driver import PIN_CRB
                if GPIO.event_detected(PIN_CRB):
                    # Hardware debounce (FR-019) has filtered transients.
                    # FR-018: valid event; FR-020: start suppression.
                    self._suppression_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS
                    self._last_raw = raw_pressed
                    return True
            except (AttributeError, NameError, TypeError):
                # GPIO or PIN_CRB not available, or event_detected() mock failed
                # Fall through to software path
                pass

        # Fallback: software qualification window (for tests and non-GPIO environments)
        # FR-019 + FR-018 + FR-020
        if raw_pressed:
            if not self._last_raw:
                # Rising edge — start qualification timer
                self._stable_start_ms = tick_time_ms
            elif self._stable_start_ms is not None:
                elapsed = tick_time_ms - self._stable_start_ms
                if elapsed >= DEBOUNCE_STABLE_MS:
                    # FR-018: valid activation (held path)
                    self._suppression_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS  # FR-020
                    self._stable_start_ms = None
                    self._last_raw = raw_pressed
                    return True
        else:
            # Released
            if self._stable_start_ms is not None:
                elapsed = tick_time_ms - self._stable_start_ms
                if elapsed >= DEBOUNCE_STABLE_MS:
                    # FR-018: valid activation (release path)
                    self._suppression_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS  # FR-020
                    self._stable_start_ms = None
                    self._last_raw = raw_pressed
                    return True
            self._stable_start_ms = None

        self._last_raw = raw_pressed
        return False
