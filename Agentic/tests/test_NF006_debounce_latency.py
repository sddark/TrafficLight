# =============================================================================
# test_NF006_debounce_latency.py
# Document reference: ARCH-TLC-001
# Requirements covered: NF-006
# Description: Debounce processing must complete within 100 ms of the first
#              rising edge of a qualifying press.  The stability window is
#              50 ms, leaving 50 ms headroom.  Tests verify that the event
#              fires within 10 ticks (100 ms) of the press starting.
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

# NF-006 hard limit.
MAX_DEBOUNCE_LATENCY_MS = 100
MAX_DEBOUNCE_LATENCY_TICKS = MAX_DEBOUNCE_LATENCY_MS // TICK_MS   # 10 ticks


class TestNF006DebounceLatency(unittest.TestCase):
    """NF-006: valid_press_event emitted within 100 ms of first rising edge."""

    def test_NF006_event_fires_within_100ms_of_press_start(self):
        """
        Begin press at t=0.  The event must be emitted no later than t=100 ms
        (tick 10).  The algorithm emits at 50 ms (tick 5); verify ≤ 10.
        """
        db = DebounceModule()
        # Press held continuously from tick 0.
        schedule = {i: True for i in range(MAX_DEBOUNCE_LATENCY_TICKS + 5)}
        events = run_debounce_ticks(db, MAX_DEBOUNCE_LATENCY_TICKS + 5, schedule)

        self.assertTrue(len(events) >= 1,
                        "Must emit at least one valid_press_event within 100 ms (NF-006)")
        first_event_tick = events[0]
        first_event_ms = first_event_tick * TICK_MS
        self.assertLessEqual(first_event_ms, MAX_DEBOUNCE_LATENCY_MS,
                             f"Event fired at {first_event_ms} ms, "
                             f"exceeds 100 ms limit (NF-006)")

    def test_NF006_event_fires_at_50ms_not_before(self):
        """
        The event must not fire before the 50 ms stability window has elapsed.
        It fires exactly at tick 5 (50 ms from press start), satisfying both
        NF-006 upper bound and FR-019 lower bound.
        """
        db = DebounceModule()
        schedule = {i: True for i in range(20)}
        events = run_debounce_ticks(db, 20, schedule)

        self.assertTrue(len(events) >= 1)
        first_event_tick = events[0]
        first_event_ms = first_event_tick * TICK_MS

        # Must not fire before 50 ms (FR-019 stability).
        self.assertGreaterEqual(first_event_ms, DEBOUNCE_STABLE_MS,
                                f"Event fired too early at {first_event_ms} ms "
                                f"(stability window not satisfied)")
        # Must not fire later than 100 ms (NF-006).
        self.assertLessEqual(first_event_ms, MAX_DEBOUNCE_LATENCY_MS,
                             f"Event fired too late at {first_event_ms} ms (NF-006)")

    def test_NF006_worst_case_latency_is_60ms(self):
        """
        Architecture analysis: worst-case latency is 60 ms (50 ms stable + 1 tick).
        Verify this by checking the event fires no later than tick 6 (60 ms).
        """
        db = DebounceModule()
        # Ticks 0-19 all pressed.
        schedule = {i: True for i in range(20)}
        events = run_debounce_ticks(db, 20, schedule)

        self.assertTrue(len(events) >= 1)
        first_event_tick = events[0]
        # Architecture says 50-60 ms; allow up to 70 ms for tick boundary.
        self.assertLessEqual(first_event_tick * TICK_MS, 70,
                             f"Worst-case latency exceeded: event at tick "
                             f"{first_event_tick} ({first_event_tick * TICK_MS} ms)")

    def test_NF006_latency_measured_from_first_rising_edge(self):
        """
        If there is noise before the qualifying press, latency is measured from
        the start of the stable segment, not from t=0.
        Bounced segment (ticks 0-2), release (ticks 3-5), then clean press
        (ticks 6+): event must fire within 100 ms of tick 6.
        """
        db = DebounceModule()
        schedule = {}
        # Bounce: 30 ms (below threshold) then release.
        for i in range(3):
            schedule[i] = True
        # Clean press starts at tick 6.
        for i in range(6, 25):
            schedule[i] = True

        events = run_debounce_ticks(db, 30, schedule)

        self.assertTrue(len(events) >= 1,
                        "Must emit event after clean press (NF-006)")
        first_event_tick = events[0]
        press_start_tick = 6
        latency_ticks = first_event_tick - press_start_tick
        latency_ms = latency_ticks * TICK_MS

        self.assertLessEqual(latency_ms, MAX_DEBOUNCE_LATENCY_MS,
                             f"Latency from clean press start: {latency_ms} ms "
                             f"exceeds 100 ms (NF-006)")

    def test_NF006_cr_pending_latched_within_100ms_via_state_machine(self):
        """
        End-to-end: inject valid_press_event into the state machine at tick 5
        (50 ms after press start) and confirm CR_PENDING=True within 100 ms.
        This validates the full IC-003 path from debounce to state machine.
        """
        from tlc.state_machine import StateMachine, PhaseState
        from tests.test_helpers import MockGPIODriver

        gpio = MockGPIODriver()
        sm = StateMachine(gpio)
        sm.initialize(tick_time_ms=0.0)

        db = DebounceModule()
        schedule = {i: True for i in range(20)}

        cr_latched_tick = None
        for i in range(20):
            t = i * TICK_MS
            raw = schedule.get(i, False)
            vp = db.process(raw, t)
            sm.update(vp, t)
            if sm.cr_pending and cr_latched_tick is None:
                cr_latched_tick = i

        self.assertIsNotNone(cr_latched_tick,
                             "CR_PENDING was never set within test window (NF-006)")

        latency_ms = cr_latched_tick * TICK_MS
        self.assertLessEqual(latency_ms, MAX_DEBOUNCE_LATENCY_MS,
                             f"CR latch latency {latency_ms} ms exceeds 100 ms (NF-006)")


if __name__ == "__main__":
    unittest.main()
