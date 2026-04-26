# =============================================================================
# test_FR018_FR020_debounce.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-018, FR-019, FR-020
# Description: Verifies DebounceModule behaviour — 50 ms stability window,
#              exactly one event per physical press, and 300 ms post-press
#              lockout.  All time is simulated; no real wall-clock is used.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest

from tlc.debounce import DebounceModule
from tests.test_helpers import (
    TICK_MS,
    DEBOUNCE_STABLE_MS,
    DEBOUNCE_LOCKOUT_MS,
    run_debounce_ticks,
)

# Ticks required to cross the 50 ms stability window (5 ticks @ 10 ms each).
STABLE_TICKS = DEBOUNCE_STABLE_MS // TICK_MS      # 5
LOCKOUT_TICKS = DEBOUNCE_LOCKOUT_MS // TICK_MS    # 30


class TestFR019StabilityWindow(unittest.TestCase):
    """FR-019: reject transitions stable < 50 ms; accept those >= 50 ms."""

    def test_FR019_press_under_50ms_is_rejected(self):
        """
        4 ticks (40 ms) of raw_pressed=True followed by release must produce
        zero valid_press_events — below the 50 ms threshold.
        """
        db = DebounceModule()
        # Press for 4 ticks (ticks 0-3), released from tick 4 onward.
        schedule = {i: True for i in range(4)}
        events = run_debounce_ticks(db, 20, schedule)
        self.assertEqual(events, [],
                         "A 40 ms press (< 50 ms threshold) must be rejected (FR-019)")

    def test_FR019_press_at_exactly_50ms_is_accepted(self):
        """
        5 ticks (50 ms) of raw_pressed=True must produce exactly one event.
        The event fires on tick 5 (elapsed_ms >= 50 on the 5th held tick).
        """
        db = DebounceModule()
        # Ticks 0-4 = pressed (5 ticks = 50 ms held before tick 5 evaluation).
        schedule = {i: True for i in range(STABLE_TICKS)}
        events = run_debounce_ticks(db, 20, schedule)
        self.assertEqual(len(events), 1,
                         "A 50 ms press must produce exactly one event (FR-019)")

    def test_FR019_press_of_49ms_boundary_rejected(self):
        """
        Press held for exactly 4 full ticks then released — 4 * 10 ms = 40 ms.
        No event expected.  (Boundary one tick below the stable threshold.)
        """
        db = DebounceModule()
        schedule = {0: True, 1: True, 2: True, 3: True}  # 40 ms
        events = run_debounce_ticks(db, 30, schedule)
        self.assertEqual(events, [],
                         "Press < 50 ms must never register (FR-019)")

    def test_FR019_press_over_200ms_yields_exactly_one_event(self):
        """
        A sustained 200 ms press (20 ticks) must still produce exactly one event
        regardless of how long the button is held.
        """
        db = DebounceModule()
        schedule = {i: True for i in range(20)}  # 200 ms
        # Run long enough to span lockout window too.
        events = run_debounce_ticks(db, 50, schedule)
        self.assertEqual(len(events), 1,
                         "A 200 ms press must produce exactly one event (FR-019/FR-018)")

    def test_FR019_intermittent_bounce_before_stable_is_rejected(self):
        """
        Simulate contact bounce: press 20 ms, release 10 ms, press again 20 ms.
        Each press segment is < 50 ms, so no event should fire.
        """
        db = DebounceModule()
        # Ticks 0-1 = pressed (20 ms), tick 2 = released, ticks 3-4 = pressed (20 ms)
        schedule = {0: True, 1: True, 3: True, 4: True}
        events = run_debounce_ticks(db, 20, schedule)
        self.assertEqual(events, [],
                         "Bounced press segments each < 50 ms must produce no event")


class TestFR018ExactlyOnePressEvent(unittest.TestCase):
    """FR-018: one physical press registers as exactly one logical press event."""

    def test_FR018_long_press_one_event(self):
        """Hold button for 500 ms — must produce exactly one event."""
        db = DebounceModule()
        schedule = {i: True for i in range(50)}  # 500 ms
        events = run_debounce_ticks(db, 60, schedule)
        self.assertEqual(len(events), 1,
                         "500 ms press must yield exactly one press event (FR-018)")

    def test_FR018_press_release_press_after_lockout_two_events(self):
        """
        Two well-separated presses (> 300 ms apart) must each produce one event
        — total of two events.
        """
        db = DebounceModule()
        first_press_start = 0
        # First press: ticks 0-9 (100 ms, well above 50 ms)
        # Lockout: 300 ms = 30 ticks from when event fires (around tick 5).
        # Event fires around tick 5; lockout expires around tick 35.
        # Second press: ticks 40-50 (100 ms after lockout clears).
        schedule = {}
        for i in range(10):
            schedule[i] = True            # first press
        for i in range(40, 50):
            schedule[i] = True            # second press (after lockout)

        events = run_debounce_ticks(db, 80, schedule)
        self.assertEqual(len(events), 2,
                         "Two presses separated by > lockout must yield two events")

    def test_FR018_no_spurious_event_on_release(self):
        """Releasing the button must never emit a valid_press_event."""
        db = DebounceModule()
        # All False — pure releases — no event expected.
        schedule = {}
        events = run_debounce_ticks(db, 30, schedule)
        self.assertEqual(events, [], "No events on all-released signal")


class TestFR020PostPressLockout(unittest.TestCase):
    """FR-020: 300 ms post-press lockout after each valid press."""

    def test_FR020_second_press_within_lockout_rejected(self):
        """
        A second press that begins during the 300 ms lockout window must be
        rejected — zero additional events.
        """
        db = DebounceModule()
        # First press: ticks 0-9 (event fires ~tick 5, lockout until ~tick 35).
        # Second press: ticks 15-25 (within lockout window).
        schedule = {}
        for i in range(10):
            schedule[i] = True
        for i in range(15, 25):
            schedule[i] = True
        events = run_debounce_ticks(db, 40, schedule)
        self.assertEqual(len(events), 1,
                         "Press inside lockout window must be rejected (FR-020)")

    def test_FR020_second_press_at_lockout_boundary_rejected(self):
        """
        Second press starting at exactly lockout_end - 1 tick must also be
        rejected.  The lockout is inclusive on the last ms.
        Event fires at tick 5 (first tick where elapsed >= 50 ms from tick 0).
        Lockout until tick 5 + 30 = 35.  Press starting at tick 34 is inside.
        """
        db = DebounceModule()
        for i in range(10):
            # first press ticks 0-9
            pass
        schedule = {i: True for i in range(10)}
        # The event fires at tick 5 (elapsed_ms from tick 0 to tick 5 = 50 ms).
        # Lockout = 300 ms = 30 ticks from tick 5 → expires after tick 35.
        # Second press at tick 34 (still inside lockout).
        for i in range(34, 44):
            schedule[i] = True
        events = run_debounce_ticks(db, 60, schedule)
        self.assertEqual(len(events), 1,
                         "Press at lockout boundary - 1 tick must be rejected (FR-020)")

    def test_FR020_lockout_expires_at_300ms_second_press_accepted(self):
        """
        After the 300 ms lockout expires, a new valid press must be accepted.
        Event fires at tick 5; lockout expires at tick 35.
        Second press from tick 40 onward (well past lockout) must produce event.
        """
        db = DebounceModule()
        schedule = {}
        for i in range(10):
            schedule[i] = True       # first press
        for i in range(40, 55):
            schedule[i] = True       # second press (after lockout)
        events = run_debounce_ticks(db, 80, schedule)
        self.assertEqual(len(events), 2,
                         "Press after 300 ms lockout must be accepted (FR-020)")

    def test_FR020_multiple_presses_within_lockout_only_one_event(self):
        """
        Three back-to-back press attempts within a single lockout window must
        collectively produce only one event.
        """
        db = DebounceModule()
        # Press 1: ticks 0-9 → event at ~tick 5, lockout until ~tick 35.
        # Press 2: ticks 12-22 (within lockout).
        # Press 3: ticks 25-35 (within lockout).
        schedule = {}
        for r in [(0, 10), (12, 22), (25, 36)]:
            for i in range(*r):
                schedule[i] = True
        events = run_debounce_ticks(db, 50, schedule)
        self.assertEqual(len(events), 1,
                         "All presses within lockout must yield exactly one event")

    def test_FR020_lockout_resets_on_each_valid_press(self):
        """
        Each valid press resets the lockout timer.  Three presses each separated
        by more than 300 ms must produce three events.
        """
        db = DebounceModule()
        # Press 1: ticks 0-9, event ~tick 5, lockout until ~tick 35.
        # Press 2: ticks 40-50, event ~tick 45, lockout until ~tick 75.
        # Press 3: ticks 80-90, event ~tick 85.
        schedule = {}
        for r in [(0, 10), (40, 51), (80, 91)]:
            for i in range(*r):
                schedule[i] = True
        events = run_debounce_ticks(db, 110, schedule)
        self.assertEqual(len(events), 3,
                         "Three presses each separated by > 300 ms must yield 3 events")


class TestDebounceInitialState(unittest.TestCase):
    """Verify the module initialises with the correct internal state."""

    def test_FR018_initial_no_event_on_first_release_tick(self):
        """First tick with raw_pressed=False must return False."""
        db = DebounceModule()
        result = db.process(False, 0.0)
        self.assertFalse(result, "First released tick must not produce event")

    def test_FR019_initial_short_press_then_release_no_event(self):
        """One tick pressed then immediately released must produce no event."""
        db = DebounceModule()
        self.assertFalse(db.process(True, 0.0))
        self.assertFalse(db.process(False, TICK_MS))


if __name__ == "__main__":
    unittest.main()
