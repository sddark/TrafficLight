# =============================================================================
# tlc/state_machine.py
# Document reference: ARCH-TLC-001
#
# Responsibilities:
#   - Implement the Traffic Light Controller (TLC) finite state machine.
#   - Define the four normal operating phases: GREEN, YELLOW, RED, PEDESTRIAN WALK.
#   - Manage the Crosswalk Request (CR) latch: set on valid press, cleared after
#     the PEDESTRIAN WALK phase completes (FR-007 through FR-013).
#   - Drive GPIO LED outputs on every phase transition via the injected gpio
#     driver (MockGPIODriver in tests; tlc.gpio_driver module in production).
#   - Detect undefined state values and enter the safe S_ERROR state (C-004).
#
# State transition table (normal operation, no CR):
#   S1_GREEN  → S2_YELLOW  after DURATION_GREEN_MS   (NF-001)
#   S2_YELLOW → S3_RED     after DURATION_YELLOW_MS   (NF-002)
#   S3_RED    → S1_GREEN   after DURATION_RED_MS      (NF-003)  [CR_PENDING=False]
#   S3_RED    → S4_PED     after DURATION_RED_MS      (NF-003)  [CR_PENDING=True]
#   S4_PED    → S1_GREEN   after DURATION_PED_MS      (NF-004)
#
# CR latch rules:
#   - Valid press in S1_GREEN, S2_YELLOW, or S3_RED: set CR_PENDING=True (FR-007,
#     FR-011, FR-015).
#   - Valid press in S4_PED: ignored entirely — CR_PENDING not set (FR-012).
#   - Redundant press when CR_PENDING already True: discarded (FR-013).
#   - CR_PENDING cleared when S4_PED transitions to S1_GREEN (FR-010).
#
# Error state (C-004):
#   Any current_state value not registered in PhaseState triggers enter_error_state(),
#   which illuminates red only and raises RuntimeError to halt the process.
#
# Assumptions:
#   - update() is called once per 10 ms tick with a monotonically increasing
#     tick_time_ms (NF-005).
#   - gpio is a duck-typed object exposing gpio_set_leds(red, yellow, green).
#   - sm.current_state and sm.cr_pending are public attributes; tests read and
#     write them directly.
# =============================================================================

from enum import IntEnum
from tlc.timing import (
    DURATION_GREEN_MS,
    DURATION_YELLOW_MS,
    DURATION_RED_MS,
    DURATION_PED_MS,
)


class PhaseState(IntEnum):
    """Enumeration of all valid TLC phase states (ARCH-TLC-001 §8.5.3)."""
    S1_GREEN  = 1
    S2_YELLOW = 2
    S3_RED    = 3
    S4_PED    = 4
    S_ERROR   = 99  # C-004: fault/halt state — red only, no further transitions


# GPIO output map for each phase state.
# Tuple layout: (red, yellow, green) — True means the LED is ON.
# FR-005: exactly one element is True per entry (single-LED invariant).
_LED_OUTPUTS_PER_STATE: dict[PhaseState, tuple[bool, bool, bool]] = {
    PhaseState.S1_GREEN:  (False, False, True),   # FR-002: GPIO22 ON
    PhaseState.S2_YELLOW: (False, True,  False),  # FR-003: GPIO27 ON
    PhaseState.S3_RED:    (True,  False, False),  # FR-004: GPIO17 ON
    PhaseState.S4_PED:    (True,  False, False),  # FR-009: GPIO17 ON (shared with RED)
    PhaseState.S_ERROR:   (True,  False, False),  # C-004:  GPIO17 ON, process halted
}


class StateMachine:
    """
    Traffic Light Controller finite state machine.

    Accepts a gpio driver object at construction time so that the same class
    is used unmodified in both production (real RPi GPIO) and unit tests
    (MockGPIODriver).
    """

    def __init__(self, gpio) -> None:
        """
        Construct the state machine without driving any GPIO outputs.

        GPIO writes are deferred to initialize() so that the LEDs-off window
        between gpio_init() and the first GREEN write is as short as possible
        (FR-017).

        Args:
            gpio: Object exposing gpio_set_leds(red, yellow, green).
                  In production this is the tlc.gpio_driver module.
                  In tests this is a MockGPIODriver instance.
        """
        self._gpio = gpio
        self.current_state: PhaseState = PhaseState.S1_GREEN  # FR-016: power-on state
        self.cr_pending: bool = False                          # FR-016: no phantom CR at startup
        self.phase_start_ms: float = 0.0

    def initialize(self, tick_time_ms: float) -> None:
        """
        Apply the initial GREEN phase GPIO output and record the phase start time.

        Must be called once after gpio_init() and before the main loop.  Keeping
        the GPIO write inside initialize() (not __init__) minimises the dark window
        between all-LEDs-off and GREEN-on (FR-017).

        Args:
            tick_time_ms: Current monotonic time in milliseconds (from now_ms()).
        """
        # FR-016: enter GREEN on power-on; FR-017: GPIO set before main loop
        self.phase_start_ms = tick_time_ms
        self._apply_state_gpio_outputs(PhaseState.S1_GREEN)

    def update(self, valid_press_event: bool, tick_time_ms: float) -> "PhaseState":
        """
        Advance the state machine by one tick.

        Called once per 10 ms tick by the main loop.  Processes any pending CR
        event, validates the current state, evaluates phase timers, and applies
        any resulting transition.

        Args:
            valid_press_event: True when the debounce module has confirmed a
                               physical button press this tick (FR-006).
            tick_time_ms:      Current monotonic time in milliseconds.

        Returns:
            The current PhaseState after this tick (may be unchanged).

        Raises:
            RuntimeError: If current_state is not a valid PhaseState member (C-004).
        """
        # ------------------------------------------------------------------
        # Step 1: Process CR press event (FR-006: monitored at all times).
        # ------------------------------------------------------------------
        if valid_press_event:
            if self.current_state == PhaseState.S4_PED:
                pass  # FR-012: press during PEDESTRIAN WALK is completely ignored
            elif not self.cr_pending:
                self.cr_pending = True  # FR-007/FR-011/FR-015: latch CR_PENDING
            # FR-013: CR_PENDING already True — discard the redundant press event

        # ------------------------------------------------------------------
        # Step 2: Validate current state value.
        # Any integer not registered in PhaseState triggers the error handler.
        # ------------------------------------------------------------------
        try:
            currently_valid_state = PhaseState(self.current_state)
        except ValueError:
            # C-004: undefined state detected — enter safe halt state
            self.enter_error_state()
            return self.current_state   # unreachable; enter_error_state() raises

        # ------------------------------------------------------------------
        # Step 3: Error state is a terminal absorbing state — no transitions.
        # ------------------------------------------------------------------
        if currently_valid_state == PhaseState.S_ERROR:
            return self.current_state

        # ------------------------------------------------------------------
        # Step 4: Evaluate phase timer and determine the next state.
        # ------------------------------------------------------------------
        milliseconds_elapsed_in_current_phase = tick_time_ms - self.phase_start_ms
        next_state: PhaseState | None = None

        if currently_valid_state == PhaseState.S1_GREEN:
            if milliseconds_elapsed_in_current_phase >= DURATION_GREEN_MS:   # NF-001
                next_state = PhaseState.S2_YELLOW                            # FR-001

        elif currently_valid_state == PhaseState.S2_YELLOW:
            if milliseconds_elapsed_in_current_phase >= DURATION_YELLOW_MS:  # NF-002
                next_state = PhaseState.S3_RED                               # FR-001

        elif currently_valid_state == PhaseState.S3_RED:
            if milliseconds_elapsed_in_current_phase >= DURATION_RED_MS:     # NF-003
                if self.cr_pending:
                    self.cr_pending = False           # FR-010: clear CR on entry to PED walk
                    next_state = PhaseState.S4_PED    # FR-008, FR-011: CR honoured
                else:
                    next_state = PhaseState.S1_GREEN  # FR-001: normal cycle continues

        elif currently_valid_state == PhaseState.S4_PED:
            if milliseconds_elapsed_in_current_phase >= DURATION_PED_MS:     # NF-004
                next_state = PhaseState.S1_GREEN

        # ------------------------------------------------------------------
        # Step 5: Apply transition if the phase timer expired.
        # ------------------------------------------------------------------
        if next_state is not None:
            self.current_state = next_state
            self.phase_start_ms = tick_time_ms      # NF-005: reset timer at transition
            self._apply_state_gpio_outputs(next_state)

        return self.current_state

    def _apply_state_gpio_outputs(self, state: PhaseState) -> None:
        """
        Write the LED outputs corresponding to the given state.

        FR-005: the _LED_OUTPUTS_PER_STATE map guarantees exactly one LED is HIGH
        per call; this method never constructs its own (red, yellow, green) tuple.

        Args:
            state: The PhaseState whose LED pattern should be applied.
        """
        red_led_on, yellow_led_on, green_led_on = _LED_OUTPUTS_PER_STATE[state]
        self._gpio.gpio_set_leds(red_led_on, yellow_led_on, green_led_on)

    def enter_error_state(self) -> None:
        """
        Enter the safe fault state: illuminate red only and raise RuntimeError.

        Called when update() detects an undefined current_state value (C-004).
        Sets current_state to S_ERROR, clears cr_pending, drives red LED on,
        and raises RuntimeError so the main loop's except block can log and exit.

        Raises:
            RuntimeError: Always — signals the process to call sys.exit(1).
        """
        # C-004: illuminate red only and halt — no further cycling
        self.current_state = PhaseState.S_ERROR
        self.cr_pending = False
        self._gpio.gpio_set_leds(True, False, False)   # C-004: red only
        raise RuntimeError(
            "TLC entered undefined state — red only, halted"  # C-004
        )
