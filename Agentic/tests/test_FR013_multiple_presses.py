# =============================================================================
# test_FR013_multiple_presses.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-013, Edge Case C
# Description: Multiple valid presses before CR is serviced must yield exactly
#              one PEDESTRIAN WALK, and no second walk must appear in the
#              following cycle.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest

from tlc.state_machine import StateMachine, PhaseState
from tests.test_helpers import (
    MockGPIODriver,
    DURATION_GREEN_MS,
    DURATION_YELLOW_MS,
    DURATION_RED_MS,
    DURATION_PED_MS,
    TICK_MS,
    ticks_for_ms,
)


def _make_sm() -> tuple[StateMachine, MockGPIODriver]:
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


class TestFR013MultiplePressesOneWalk(unittest.TestCase):
    """FR-013, Edge Case C: multiple presses before service yield one walk only."""

    def test_FR013_second_press_when_cr_already_pending_is_discarded(self):
        """
        Second valid_press_event while CR_PENDING=True must not change state —
        CR_PENDING stays True but must not cause any additional effect.
        """
        sm, gpio = _make_sm()

        # First press — latch CR.
        sm.update(True, 0.0)
        self.assertTrue(sm.cr_pending)

        # Second press with CR already latched.
        sm.update(True, TICK_MS)
        # Still True (not doubled or reset).
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must remain True after redundant press (FR-013)")

    def test_FR013_cr_pending_is_boolean_not_counter(self):
        """
        Ten valid press events in a row while CR_PENDING=True must still result
        in CR_PENDING=True (not some incremented counter).
        """
        sm, gpio = _make_sm()
        sm.update(True, 0.0)  # latch
        for i in range(1, 11):
            sm.update(True, i * TICK_MS)
        self.assertTrue(sm.cr_pending)

        # Advance through full cycle — exactly one PED walk must occur.
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS + DURATION_PED_MS
        n = ticks_for_ms(total_ms) + 20
        s4_count = 0
        prev = sm.current_state
        for i in range(11, 11 + n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 1,
                         "Exactly one S4_PED must occur regardless of press count (FR-013)")

    def test_FR013_second_press_after_lockout_during_green_cr_already_pending(self):
        """
        Edge Case C: first press latches CR; after lockout expires a second press
        arrives during GREEN — must be discarded because CR_PENDING is already True.
        """
        sm, gpio = _make_sm()
        # First press at tick 0.
        sm.update(True, 0.0)
        self.assertTrue(sm.cr_pending)

        # Simulate lockout expiry (300 ms = 30 ticks) then second press.
        # We skip ticks 1-31 (no press) then send press at tick 32.
        for i in range(1, 32):
            sm.update(False, i * TICK_MS)
        sm.update(True, 32 * TICK_MS)      # second press after lockout
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must still be True, not reset by second press (FR-013)")

    def test_FR013_exactly_one_s4_ped_after_two_presses_in_green(self):
        """
        Two presses in GREEN (separated by > lockout) → exactly one S4_PED in
        the entire subsequent cycle.  No second walk.
        """
        sm, gpio = _make_sm()

        # Press 1 at tick 0.
        sm.update(True, 0.0)
        # No-press ticks to let lockout expire (need > 30 ticks past the event).
        # Event fires at tick 5 (50 ms stable); lockout until tick 35.
        # We simulate by directly injecting the second press_event at tick 40.
        for i in range(1, 40):
            sm.update(False, i * TICK_MS)
        sm.update(True, 40 * TICK_MS)  # press 2 (after lockout, CR already pending)

        # Continue through the rest of GREEN → YELLOW → RED → PED → GREEN.
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS + DURATION_PED_MS
        n = ticks_for_ms(total_ms) + 20
        s4_count = 0
        prev = sm.current_state
        for i in range(41, 41 + n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 1,
                         "Two presses before service must still yield exactly one "
                         "S4_PED (FR-013)")

    def test_FR013_no_second_s4_ped_in_subsequent_cycle(self):
        """
        After the first PED walk is serviced and cleared, the very next full
        cycle must complete without triggering another S4_PED (no queued request).
        """
        sm, gpio = _make_sm()

        # Multiple presses during GREEN.
        sm.update(True, 0.0)
        sm.update(True, TICK_MS)
        sm.update(True, 2 * TICK_MS)

        # Run through two full cycles: first with PED, second without.
        two_cycle_ms = (2 * (DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS)
                        + DURATION_PED_MS)
        n = ticks_for_ms(two_cycle_ms) + 30

        s4_count = 0
        green_entries = 0
        prev = PhaseState.S1_GREEN
        for i in range(3, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S1_GREEN and prev != PhaseState.S1_GREEN:
                green_entries += 1
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 1,
                         "Only one S4_PED over two full cycles (FR-013)")

    def test_FR013_presses_across_yellow_and_red_still_one_walk(self):
        """
        CR pressed in GREEN, then again in YELLOW, then again in RED — three
        presses total — must still result in exactly one PED walk.
        """
        sm, gpio = _make_sm()

        # Press in GREEN.
        sm.update(True, 0.0)

        # Advance to YELLOW, press again.
        n_green = ticks_for_ms(DURATION_GREEN_MS) + 5
        yellow_pressed = False
        red_pressed = False
        for i in range(1, n_green):
            t = i * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S2_YELLOW and not yellow_pressed:
                sm.update(True, t + TICK_MS)   # press in YELLOW
                yellow_pressed = True

        # Advance to RED, press again.
        n_yellow = ticks_for_ms(DURATION_YELLOW_MS) + 5
        for j in range(n_yellow):
            t = (n_green + j) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S3_RED and not red_pressed:
                sm.update(True, t + TICK_MS)   # press in RED
                red_pressed = True

        # Run through to end of PED walk.
        total_ms = DURATION_RED_MS + DURATION_PED_MS
        n_rest = ticks_for_ms(total_ms) + 20
        base = n_green + n_yellow
        s4_count = 0
        prev = sm.current_state
        for k in range(n_rest):
            t = (base + k) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 1,
                         "Presses across multiple phases must still yield one S4_PED (FR-013)")


if __name__ == "__main__":
    unittest.main()
