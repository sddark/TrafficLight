# =============================================================================
# tlc/debounce.py
# Document reference: ARCH-TLC-001
#
# Responsibilities:
#   - Filter raw Crosswalk Request Button (CRB) signal to reject contact bounce
#     and spurious noise (FR-018, FR-019).
#   - Emit exactly one valid_press_event per physical button press regardless
#     of how long the button is held (FR-018).
#   - Enforce a 50 ms stability window: press segments shorter than 50 ms are
#     discarded (FR-019).
#   - Enforce a 300 ms post-press lockout after each accepted event so that
#     switch chatter on release cannot trigger a second event (FR-020).
#
# Algorithm overview:
#   The module operates as a two-stage filter evaluated once per 10 ms tick:
#
#   Stage 0 — Lockout gate:
#     If a lockout is active (tick_time_ms < lockout_until_ms), all raw input
#     is absorbed and False is returned.  When the lockout expires the stability
#     timer is also reset so a new press segment is evaluated from scratch.
#
#   Stage 1 — Stability detection:
#     On a rising edge (False → True) the stability timer starts.
#     While the button remains held, elapsed time is checked each tick:
#       * elapsed >= 50 ms while held → emit True (held-path event).
#     If the button releases before the 50 ms threshold the timer is cancelled
#     (press too short — FR-019 rejection).
#     If the button releases after the 50 ms threshold:
#       * emit True (release-path event).
#
#   Both held-path and release-path events start the 300 ms lockout (FR-020).
#
# Emit timing (used by tests):
#   Rising edge at tick T (t = T*10 ms), _stable_start_ms = T*10.
#   Held-path: tick T+5 (t = (T+5)*10 ms), elapsed = 50 ms → emit.
#   Release-path (press held exactly 4 ticks, released on tick T+5):
#     At tick T+5, raw=False, elapsed = 50 ms → emit on release.
#   Both paths result in the event appearing at tick T+5 (50 ms from press start).
#
# Assumptions:
#   - process() is called exactly once per tick with a monotonically increasing
#     tick_time_ms value; no real-time clock is consulted internally.
#   - DEBOUNCE_STABLE_MS and DEBOUNCE_LOCKOUT_MS are imported from tlc.timing.
# =============================================================================

from tlc.timing import DEBOUNCE_STABLE_MS, DEBOUNCE_LOCKOUT_MS


class DebounceModule:
    """
    Single-channel contact debouncer with stability window and post-press lockout.

    All timing is driven by the tick_time_ms argument supplied to process(),
    making the module fully deterministic and testable without a real clock.
    """

    def __init__(self) -> None:
        # Last raw button state — used to detect rising and falling edges
        self._last_raw_button_state: bool = False

        # Timestamp (ms) at which the current press segment began.
        # None when no press segment is being tracked.
        self._stable_start_ms: float | None = None   # FR-019: stability timer

        # Timestamp (ms) at which the post-press lockout expires.
        # None when no lockout is active.
        self._lockout_until_ms: float | None = None  # FR-020: post-press lockout

    def process(self, raw_pressed: bool, tick_time_ms: float) -> bool:
        """
        Evaluate one tick of raw CRB input and return True when a valid press
        event is confirmed.

        Args:
            raw_pressed:  Current raw state of the CRB pin (True = pressed).
            tick_time_ms: Monotonically increasing tick timestamp in milliseconds.

        Returns:
            True exactly once per valid physical press; False otherwise.
        """
        # ------------------------------------------------------------------
        # Stage 0: FR-020 lockout gate.
        # While a lockout is active, absorb all input and return False.
        # When the lockout expires, reset the stability timer so any in-progress
        # press segment is evaluated from scratch — avoiding a false emit caused
        # by a press that started during the lockout period.
        # ------------------------------------------------------------------
        if self._lockout_until_ms is not None:
            if tick_time_ms < self._lockout_until_ms:
                # Still inside the lockout window — discard this tick's input
                self._last_raw_button_state = raw_pressed
                return False
            else:
                # Lockout has expired; reset both timers so the next edge starts fresh
                self._lockout_until_ms = None
                self._stable_start_ms = None

        # ------------------------------------------------------------------
        # Stage 1: FR-018, FR-019 stability detection.
        # ------------------------------------------------------------------
        if raw_pressed:
            if not self._last_raw_button_state:
                # Rising edge detected — start the stability timer (FR-019)
                self._stable_start_ms = tick_time_ms

            elif self._stable_start_ms is not None:
                # Button continues to be held; check whether stability window elapsed
                milliseconds_elapsed_since_press_start = tick_time_ms - self._stable_start_ms

                if milliseconds_elapsed_since_press_start >= DEBOUNCE_STABLE_MS:
                    # FR-018: valid press confirmed on the held path
                    self._lockout_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS  # FR-020
                    self._stable_start_ms = None
                    self._last_raw_button_state = raw_pressed
                    return True

        else:
            # Button is released this tick
            if self._stable_start_ms is not None:
                # A press segment was in progress — evaluate whether it met the threshold
                milliseconds_elapsed_since_press_start = tick_time_ms - self._stable_start_ms

                if milliseconds_elapsed_since_press_start >= DEBOUNCE_STABLE_MS:
                    # FR-018: valid press confirmed on the release path (button was
                    # held >= 50 ms before being released — exactly one event emitted)
                    self._lockout_until_ms = tick_time_ms + DEBOUNCE_LOCKOUT_MS  # FR-020
                    self._stable_start_ms = None
                    self._last_raw_button_state = raw_pressed
                    return True

            # Press segment too short (< 50 ms) or no segment was active —
            # cancel the stability timer (FR-019: reject sub-threshold presses)
            self._stable_start_ms = None

        self._last_raw_button_state = raw_pressed
        return False
