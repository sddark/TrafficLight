# =============================================================================
# test_helpers.py
# Document reference: ARCH-TLC-001
# Purpose: Shared fixtures and mock infrastructure for all TLC integration tests.
#
# IMPORTANT: This module must be imported BEFORE any tlc.* imports in every
# test file.  It patches sys.modules so that 'import RPi' and 'import RPi.GPIO'
# resolve to MagicMock objects on any OS (including Windows), satisfying the
# requirement that all tests run without Raspberry Pi hardware.
# =============================================================================

import sys
import importlib
from unittest.mock import MagicMock, patch, call
import types

# ---------------------------------------------------------------------------
# Step 1 — Install stub modules for RPi and RPi.GPIO before any tlc import.
# ---------------------------------------------------------------------------

_rpi_stub = MagicMock(name="RPi")
_gpio_stub = MagicMock(name="RPi.GPIO")

# Expose GPIO constants that the implementation may reference.
_gpio_stub.BCM = 11
_gpio_stub.OUT = 0
_gpio_stub.IN = 1
_gpio_stub.PUD_UP = 22
_gpio_stub.HIGH = 1
_gpio_stub.LOW = 0

# Disable event_detected so debounce.py uses software path in tests.
# On real Pi, RPi.GPIO provides this; in tests, set to None so the
# try-except in debounce.py catches TypeError and falls back to software.
_gpio_stub.event_detected = None

_rpi_stub.GPIO = _gpio_stub

sys.modules.setdefault("RPi", _rpi_stub)
sys.modules.setdefault("RPi.GPIO", _gpio_stub)

# ---------------------------------------------------------------------------
# Timing constants (duplicated here so test helpers are self-contained).
# The authoritative values live in tlc/timing.py; keep these in sync.
# ---------------------------------------------------------------------------

TICK_MS            = 10        # ms per simulated tick
DURATION_GREEN_MS  = 7000
DURATION_YELLOW_MS = 3000
DURATION_RED_MS    = 7000
DURATION_PED_MS    = 10000
DEBOUNCE_STABLE_MS = 50
DEBOUNCE_LOCKOUT_MS = 300

PIN_RED    = 17
PIN_YELLOW = 27
PIN_GREEN  = 22
PIN_CRB    = 18

# ---------------------------------------------------------------------------
# Helper: reload a tlc module so patched sys.modules take effect cleanly.
# ---------------------------------------------------------------------------

def reload_tlc_module(module_name: str):
    """Force-reload a tlc sub-module, returning the fresh module object."""
    full_name = f"tlc.{module_name}"
    if full_name in sys.modules:
        return importlib.reload(sys.modules[full_name])
    return importlib.import_module(full_name)


# ---------------------------------------------------------------------------
# Helper: build a MockGPIODriver that records calls to gpio_set_leds().
# Used by state-machine tests to inspect GPIO transitions without real GPIO.
# ---------------------------------------------------------------------------

class MockGPIODriver:
    """
    Drop-in replacement for gpio_driver module functions.
    Records every gpio_set_leds() call in self.led_calls as (red, yellow, green).
    """

    def __init__(self):
        self.led_calls: list[tuple[bool, bool, bool]] = []
        self.crb_return_value: bool = False   # False = not pressed

    def gpio_init(self) -> None:
        pass

    def gpio_cleanup(self) -> None:
        pass

    def gpio_set_leds(self, red: bool, yellow: bool, green: bool) -> None:
        self.led_calls.append((bool(red), bool(yellow), bool(green)))

    def gpio_read_crb(self) -> bool:
        return self.crb_return_value

    # Convenience: last LED state written
    @property
    def last_leds(self) -> tuple[bool, bool, bool] | None:
        return self.led_calls[-1] if self.led_calls else None


# ---------------------------------------------------------------------------
# Helper: drive N ticks through the state machine, returning state history.
# tick_time_ms advances by TICK_MS each call.
# press_ticks: set of tick indices (0-based) at which valid_press_event=True.
# ---------------------------------------------------------------------------

def run_ticks(sm, n_ticks: int, start_ms: float = 0.0,
              press_ticks: set | None = None) -> list:
    """
    Drive the state machine for n_ticks ticks.
    Returns a list of (tick_index, tick_time_ms, returned_state) tuples.
    """
    if press_ticks is None:
        press_ticks = set()
    history = []
    for i in range(n_ticks):
        t = start_ms + i * TICK_MS
        valid_press = i in press_ticks
        state = sm.update(valid_press, t)
        history.append((i, t, state))
    return history


# ---------------------------------------------------------------------------
# Helper: drive the debounce module for N ticks with a given raw_pressed
# schedule.  raw_schedule is a dict {tick_index: raw_pressed_bool}.
# Ticks not in the dict default to False (released).
# Returns list of (tick_index, returned_bool) for all ticks where True.
# ---------------------------------------------------------------------------

def run_debounce_ticks(db, n_ticks: int, raw_schedule: dict,
                       start_ms: float = 0.0) -> list:
    """
    Drive the debounce module for n_ticks ticks.
    Returns list of tick indices at which a valid_press_event was emitted.
    """
    events = []
    for i in range(n_ticks):
        t = start_ms + i * TICK_MS
        raw = raw_schedule.get(i, False)
        result = db.process(raw, t)
        if result:
            events.append(i)
    return events


# ---------------------------------------------------------------------------
# Helper: ticks needed to cover a duration, ceiling-rounded to tick boundary.
# ---------------------------------------------------------------------------

def ticks_for_ms(duration_ms: float) -> int:
    import math
    return math.ceil(duration_ms / TICK_MS)
