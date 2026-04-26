# =============================================================================
# test_FR015_cr_during_yellow.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-015, Edge Case A
# Description: CR registered during YELLOW phase — YELLOW must not be
#              shortened, CR must survive into RED, and PEDESTRIAN WALK must
#              follow RED.
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


def _make_sm_at_yellow_entry() -> tuple[StateMachine, MockGPIODriver, int]:
    """
    Return (sm, gpio, yellow_entry_tick) with the SM just having transitioned
    into S2_YELLOW.  No CR has been pressed yet.
    """
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)

    n_green = ticks_for_ms(DURATION_GREEN_MS) + 5
    entry_tick = None
    prev = PhaseState.S1_GREEN
    for i in range(1, n_green):
        t = i * TICK_MS
        s = sm.update(False, t)
        if s == PhaseState.S2_YELLOW and prev == PhaseState.S1_GREEN:
            entry_tick = i
            break
        prev = s

    assert entry_tick is not None, "Did not reach S2_YELLOW"
    return sm, gpio, entry_tick


class TestFR015CRLatchedDuringYellow(unittest.TestCase):
    """FR-015: valid press during YELLOW latches CR_PENDING."""

    def test_FR015_cr_pending_set_on_press_in_yellow(self):
        """Valid press at the start of YELLOW must set CR_PENDING = True."""
        sm, gpio, y_tick = _make_sm_at_yellow_entry()
        self.assertEqual(sm.current_state, PhaseState.S2_YELLOW)
        self.assertFalse(sm.cr_pending)

        # Inject press on the first tick inside YELLOW.
        t = (y_tick + 1) * TICK_MS
        sm.update(True, t)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must be True after press in S2_YELLOW (FR-015)")

    def test_FR015_yellow_not_shortened_after_cr(self):
        """YELLOW must run its full duration even after CR is latched."""
        sm, gpio, y_tick = _make_sm_at_yellow_entry()

        # Latch CR immediately upon entering YELLOW.
        t_press = (y_tick + 1) * TICK_MS
        sm.update(True, t_press)
        self.assertTrue(sm.cr_pending)

        # Check we are still in YELLOW after half the YELLOW duration.
        half_yellow_ticks = ticks_for_ms(DURATION_YELLOW_MS // 2)
        for j in range(2, half_yellow_ticks):
            t = (y_tick + j) * TICK_MS
            sm.update(False, t)
        self.assertEqual(sm.current_state, PhaseState.S2_YELLOW,
                         "YELLOW must not be shortened by CR latch (FR-015)")

    def test_FR015_cr_pending_survives_into_red(self):
        """CR_PENDING must be True when YELLOW transitions to RED."""
        sm, gpio, y_tick = _make_sm_at_yellow_entry()

        # Press during YELLOW.
        sm.update(True, (y_tick + 1) * TICK_MS)

        # Advance through the rest of YELLOW.
        n_yellow = ticks_for_ms(DURATION_YELLOW_MS) + 5
        prev = PhaseState.S2_YELLOW
        for j in range(2, n_yellow):
            t = (y_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S3_RED and prev == PhaseState.S2_YELLOW:
                break
            prev = s

        self.assertEqual(sm.current_state, PhaseState.S3_RED)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must survive YELLOW→RED (FR-015)")


class TestFR015StateSequenceWithYellowCR(unittest.TestCase):
    """FR-015, Edge Case A: full sequence S2→S3→S4→S1 after CR in YELLOW."""

    def test_FR015_sequence_yellow_red_ped_green(self):
        """
        Press during YELLOW → sequence must be YELLOW→RED→PED→GREEN.
        No extra GREEN between RED and PED.
        """
        sm, gpio, y_tick = _make_sm_at_yellow_entry()
        sm.update(True, (y_tick + 1) * TICK_MS)  # CR in YELLOW

        total_after_ms = DURATION_YELLOW_MS + DURATION_RED_MS + DURATION_PED_MS
        n_after = ticks_for_ms(total_after_ms) + 20

        state_seq = []
        prev = PhaseState.S2_YELLOW
        for j in range(2, n_after):
            t = (y_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                state_seq.append(s)
                prev = s

        self.assertIn(PhaseState.S3_RED, state_seq, "S3_RED must follow YELLOW")
        self.assertIn(PhaseState.S4_PED, state_seq, "S4_PED must follow RED (FR-015)")
        self.assertIn(PhaseState.S1_GREEN, state_seq,
                      "S1_GREEN must follow S4_PED (FR-015)")

        # Ordering check.
        def _idx(state):
            return state_seq.index(state)

        self.assertLess(_idx(PhaseState.S3_RED), _idx(PhaseState.S4_PED))
        self.assertLess(_idx(PhaseState.S4_PED), _idx(PhaseState.S1_GREEN))

    def test_FR015_no_green_inserted_between_red_and_ped(self):
        """
        After CR in YELLOW, there must be no GREEN phase between RED and PED.
        Edge Case A: transition must go S3_RED → S4_PED directly.
        """
        sm, gpio, y_tick = _make_sm_at_yellow_entry()
        sm.update(True, (y_tick + 1) * TICK_MS)

        total_after_ms = DURATION_YELLOW_MS + DURATION_RED_MS + DURATION_PED_MS
        n_after = ticks_for_ms(total_after_ms) + 20

        state_seq = []
        prev = PhaseState.S2_YELLOW
        for j in range(2, n_after):
            t = (y_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                state_seq.append(s)
                prev = s

        # Verify S3_RED is immediately followed by S4_PED (no S1_GREEN in between).
        red_idx = state_seq.index(PhaseState.S3_RED)
        ped_idx = state_seq.index(PhaseState.S4_PED)
        self.assertEqual(ped_idx, red_idx + 1,
                         "S4_PED must immediately follow S3_RED — no S1_GREEN in between")

    def test_FR015_cr_already_pending_second_yellow_press_ignored(self):
        """
        If CR is already True when a second press arrives in YELLOW, it must be
        discarded — CR_PENDING remains True but does not double-count (FR-013).
        """
        sm, gpio, y_tick = _make_sm_at_yellow_entry()

        t1 = (y_tick + 1) * TICK_MS
        sm.update(True, t1)  # first press
        self.assertTrue(sm.cr_pending)

        t2 = (y_tick + 3) * TICK_MS
        sm.update(True, t2)  # second press (should be discarded)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must still be True after redundant press (FR-013)")

        # The test succeeds as long as cr_pending is still a simple bool True,
        # not some incremented counter.  We verify by running through to PED
        # and confirming exactly one S4_PED.
        total_ms = DURATION_YELLOW_MS + DURATION_RED_MS + DURATION_PED_MS
        n = ticks_for_ms(total_ms) + 20
        s4_count = 0
        prev = PhaseState.S2_YELLOW
        for j in range(4, n):
            t = (y_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s
        self.assertEqual(s4_count, 1, "Exactly one S4_PED must follow (FR-013)")


if __name__ == "__main__":
    unittest.main()
