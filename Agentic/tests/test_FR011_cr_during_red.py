# =============================================================================
# test_FR011_cr_during_red.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-011, Edge Case D
# Description: CR registered during RED phase — RED must complete its full
#              nominal duration before transitioning to PEDESTRIAN WALK.
#              No early exit from RED is permitted.
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

# Tolerance for phase timing assertions.
TOLERANCE_MS = 200


def _make_sm_at_red_entry() -> tuple[StateMachine, MockGPIODriver, int]:
    """
    Advance to the moment S3_RED is entered and return (sm, gpio, red_entry_tick).
    """
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)

    n = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 15
    entry_tick = None
    prev = PhaseState.S1_GREEN
    for i in range(1, n):
        t = i * TICK_MS
        s = sm.update(False, t)
        if s == PhaseState.S3_RED and prev != PhaseState.S3_RED:
            entry_tick = i
            break
        prev = s

    assert entry_tick is not None, "Did not reach S3_RED"
    return sm, gpio, entry_tick


class TestFR011CRDuringRed(unittest.TestCase):
    """FR-011: press during RED — full RED duration first, then PED WALK."""

    def test_FR011_cr_pending_latched_during_red(self):
        """Valid press at any point during RED must set CR_PENDING = True."""
        sm, gpio, r_tick = _make_sm_at_red_entry()
        self.assertEqual(sm.current_state, PhaseState.S3_RED)
        self.assertFalse(sm.cr_pending)

        t = (r_tick + 1) * TICK_MS
        sm.update(True, t)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must be True after press in S3_RED (FR-011)")

    def test_FR011_red_completes_full_duration_after_early_press(self):
        """
        CR pressed 1 tick into RED — RED must still run DURATION_RED_MS before
        transitioning to S4_PED.  Minimum ticks of RED measured must be >= nominal.
        """
        sm, gpio, r_tick = _make_sm_at_red_entry()
        # Press on the first tick inside RED.
        sm.update(True, (r_tick + 1) * TICK_MS)

        # Track how long we stay in RED.
        red_ticks = 1  # already consumed one tick above
        n_red = ticks_for_ms(DURATION_RED_MS) + 20
        for j in range(2, n_red):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != PhaseState.S3_RED:
                break
            red_ticks += 1

        red_duration_ms = red_ticks * TICK_MS
        self.assertGreaterEqual(
            red_duration_ms, DURATION_RED_MS - TOLERANCE_MS,
            f"RED phase exited too early: {red_duration_ms} ms "
            f"(expected >= {DURATION_RED_MS - TOLERANCE_MS} ms) (FR-011)"
        )

    def test_FR011_red_phase_not_extended_by_cr(self):
        """
        RED must also not run longer than its nominal + tolerance even with CR.
        CR must not extend RED; it only influences the *next* state.
        """
        sm, gpio, r_tick = _make_sm_at_red_entry()
        sm.update(True, (r_tick + 1) * TICK_MS)

        red_ticks = 1
        n_max = ticks_for_ms(DURATION_RED_MS + TOLERANCE_MS) + 10
        for j in range(2, n_max):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != PhaseState.S3_RED:
                break
            red_ticks += 1

        red_duration_ms = red_ticks * TICK_MS
        self.assertLessEqual(
            red_duration_ms, DURATION_RED_MS + TOLERANCE_MS,
            f"RED phase ran too long: {red_duration_ms} ms (FR-011)"
        )

    def test_FR011_ped_walk_follows_immediately_after_red(self):
        """
        After full RED with CR, next state must be S4_PED, not S1_GREEN.
        Edge Case D: the correct successor is PED WALK, not another normal phase.
        """
        sm, gpio, r_tick = _make_sm_at_red_entry()
        sm.update(True, (r_tick + 1) * TICK_MS)

        n = ticks_for_ms(DURATION_RED_MS) + 15
        prev = PhaseState.S3_RED
        successor = None
        for j in range(2, n):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                successor = s
                break
            prev = s

        self.assertEqual(successor, PhaseState.S4_PED,
                         "S4_PED must follow S3_RED when CR is pending (FR-011)")

    def test_FR011_cr_pressed_at_instant_red_begins_honored(self):
        """
        Edge Case D: CR pressed on the very first tick of RED.
        System must still wait the full RED duration, then go to PED.
        """
        sm, gpio, r_tick = _make_sm_at_red_entry()
        # Press exactly on the entry tick (same tick as transition into RED).
        sm.update(True, r_tick * TICK_MS)
        self.assertTrue(sm.cr_pending)

        n = ticks_for_ms(DURATION_RED_MS) + 15
        prev = PhaseState.S3_RED
        successor = None
        for j in range(1, n):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                successor = s
                break
            prev = s

        self.assertEqual(successor, PhaseState.S4_PED,
                         "Immediate press on RED entry must still lead to PED (Edge Case D)")

    def test_FR011_ped_walk_duration_correct_after_red_cr(self):
        """PEDESTRIAN WALK following a RED-phase CR must still be DURATION_PED_MS."""
        sm, gpio, r_tick = _make_sm_at_red_entry()
        sm.update(True, (r_tick + 1) * TICK_MS)

        # Advance past RED.
        n_red = ticks_for_ms(DURATION_RED_MS) + 15
        ped_entry_tick = None
        prev = PhaseState.S3_RED
        for j in range(2, n_red):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                ped_entry_tick = r_tick + j
                break
            prev = s

        self.assertIsNotNone(ped_entry_tick, "S4_PED must be entered")

        # Measure PED duration.
        ped_ticks = 0
        n_ped = ticks_for_ms(DURATION_PED_MS + TOLERANCE_MS) + 10
        for k in range(n_ped):
            t = (ped_entry_tick + k) * TICK_MS
            s = sm.update(False, t)
            if s != PhaseState.S4_PED:
                break
            ped_ticks += 1

        ped_ms = ped_ticks * TICK_MS
        self.assertGreaterEqual(ped_ms, DURATION_PED_MS - TOLERANCE_MS,
                                f"PED duration too short: {ped_ms} ms")
        self.assertLessEqual(ped_ms, DURATION_PED_MS + TOLERANCE_MS,
                             f"PED duration too long: {ped_ms} ms")


class TestFR011NoCREarlyExitFromRed(unittest.TestCase):
    """Without CR, RED must transition directly to GREEN (no PED inserted)."""

    def test_FR011_no_cr_red_goes_to_green(self):
        """Without a press in RED, S3_RED must go to S1_GREEN, not S4_PED."""
        sm, gpio, r_tick = _make_sm_at_red_entry()
        self.assertFalse(sm.cr_pending)

        n = ticks_for_ms(DURATION_RED_MS) + 15
        prev = PhaseState.S3_RED
        successor = None
        for j in range(1, n):
            t = (r_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                successor = s
                break
            prev = s

        self.assertEqual(successor, PhaseState.S1_GREEN,
                         "Without CR, RED must go to GREEN (no PED)")


if __name__ == "__main__":
    unittest.main()
