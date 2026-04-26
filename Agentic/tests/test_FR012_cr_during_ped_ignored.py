# =============================================================================
# test_FR012_cr_during_ped_ignored.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-012, Edge Case B
# Description: CR pressed during PEDESTRIAN WALK is completely ignored —
#              CR_PENDING must not be set, the phase duration must not be
#              extended, and the subsequent cycle must be a plain GREEN→YELLOW→RED
#              with no second PED walk.
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

TOLERANCE_MS = 200


def _make_sm_at_ped_entry() -> tuple[StateMachine, MockGPIODriver, int]:
    """
    Advance to the moment S4_PED is entered by injecting a CR during GREEN.
    Returns (sm, gpio, ped_entry_tick).
    """
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)

    # Latch CR on tick 1 (during GREEN).
    sm.update(True, TICK_MS)

    lead_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
    n = ticks_for_ms(lead_ms) + 15
    entry_tick = None
    prev = PhaseState.S1_GREEN
    for i in range(2, n):
        t = i * TICK_MS
        s = sm.update(False, t)
        if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
            entry_tick = i
            break
        prev = s

    assert entry_tick is not None, "Did not reach S4_PED"
    return sm, gpio, entry_tick


class TestFR012PressIgnoredDuringPed(unittest.TestCase):
    """FR-012: press during PEDESTRIAN WALK must be entirely discarded."""

    def test_FR012_cr_pending_not_set_by_press_in_s4_ped(self):
        """
        CR_PENDING must remain False when a valid_press_event arrives in S4_PED.
        (CR_PENDING was cleared on entry to S4_PED per FR-010; press in S4 must not re-set it.)
        """
        sm, gpio, p_tick = _make_sm_at_ped_entry()
        self.assertEqual(sm.current_state, PhaseState.S4_PED)
        # CR was cleared when we entered S4_PED from RED.
        self.assertFalse(sm.cr_pending,
                         "CR_PENDING must be False at S4_PED entry")

        # Inject press during PED.
        t_press = (p_tick + 5) * TICK_MS
        sm.update(True, t_press)
        self.assertFalse(sm.cr_pending,
                         "CR_PENDING must not be set by press during S4_PED (FR-012)")

    def test_FR012_multiple_presses_during_ped_all_ignored(self):
        """
        Three valid press events during S4_PED must all be discarded.
        CR_PENDING must remain False throughout.
        """
        sm, gpio, p_tick = _make_sm_at_ped_entry()
        for offset in [3, 10, 20]:
            t = (p_tick + offset) * TICK_MS
            sm.update(True, t)
            self.assertFalse(sm.cr_pending,
                             f"CR_PENDING must remain False after press at offset "
                             f"+{offset} ticks into PED (FR-012)")

    def test_FR012_ped_duration_not_extended_by_press(self):
        """
        Press during S4_PED must not extend its duration beyond DURATION_PED_MS.
        """
        sm, gpio, p_tick = _make_sm_at_ped_entry()

        # Inject press at the midpoint of PED.
        mid_offset = ticks_for_ms(DURATION_PED_MS // 2)
        sm.update(True, (p_tick + mid_offset) * TICK_MS)

        # Count how many ticks we remain in S4_PED from entry.
        ped_ticks = mid_offset  # already consumed
        n_max = ticks_for_ms(DURATION_PED_MS + TOLERANCE_MS) + 10
        for j in range(mid_offset + 1, n_max):
            t = (p_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != PhaseState.S4_PED:
                break
            ped_ticks += 1

        ped_ms = ped_ticks * TICK_MS
        self.assertLessEqual(ped_ms, DURATION_PED_MS + TOLERANCE_MS,
                             f"PED was extended to {ped_ms} ms — press must not "
                             f"extend PED duration (FR-012)")

    def test_FR012_state_returns_to_green_after_ped_not_second_ped(self):
        """
        After S4_PED completes (even with press ignored), next state must be
        S1_GREEN, not a second S4_PED.
        """
        sm, gpio, p_tick = _make_sm_at_ped_entry()

        # Press near start of PED.
        sm.update(True, (p_tick + 2) * TICK_MS)

        n = ticks_for_ms(DURATION_PED_MS) + 15
        prev = PhaseState.S4_PED
        successor = None
        for j in range(3, n):
            t = (p_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != prev:
                successor = s
                break
            prev = s

        self.assertEqual(successor, PhaseState.S1_GREEN,
                         "S1_GREEN must follow S4_PED even after ignored press (FR-012)")

    def test_FR012_next_full_cycle_has_no_second_ped_walk(self):
        """
        Edge Case B: The cycle following a completed PED walk (where a press
        was ignored) must be plain GREEN→YELLOW→RED without S4_PED.
        """
        sm, gpio, p_tick = _make_sm_at_ped_entry()
        # Ignored press in PED.
        sm.update(True, (p_tick + 5) * TICK_MS)

        # Advance through the rest of PED + one full subsequent cycle.
        total_after_ms = DURATION_PED_MS + DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(total_after_ms) + 25
        s4_count_after = 0
        green_seen = False
        prev = PhaseState.S4_PED
        for j in range(6, n):
            t = (p_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S1_GREEN:
                green_seen = True
            # Count S4_PED entries *after* the first time we see S1_GREEN.
            if green_seen and s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count_after += 1
            prev = s

        self.assertEqual(s4_count_after, 0,
                         "No second S4_PED must occur in the cycle after an ignored "
                         "PED press (FR-012, Edge Case B)")


if __name__ == "__main__":
    unittest.main()
