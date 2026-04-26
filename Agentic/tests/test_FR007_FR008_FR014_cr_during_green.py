# =============================================================================
# test_FR007_FR008_FR014_cr_during_green.py
# Document reference: ARCH-TLC-001
# Requirements covered: FR-007, FR-008, FR-014, Edge Case E
# Description: CR latched during GREEN, carried through YELLOW and RED,
#              PEDESTRIAN WALK inserted after RED, cleared on exit, and normal
#              cycling resumes without a second walk.
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


def _run_ticks(sm, n, start=0.0, press_at: int | None = None):
    """Drive SM for n ticks; optionally inject a press at tick press_at."""
    for i in range(n):
        t = start + i * TICK_MS
        vp = (i == press_at)
        sm.update(vp, t)


class TestFR007CRPendingLatchedDuringGreen(unittest.TestCase):
    """FR-007: a valid press during GREEN sets CR_PENDING = True."""

    def test_FR007_cr_pending_true_after_press_in_green(self):
        """CR_PENDING must become True immediately upon valid_press_event during S1_GREEN."""
        sm, gpio = _make_sm()
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN)
        self.assertFalse(sm.cr_pending)

        # Inject a valid press on the very first tick (still in GREEN).
        sm.update(True, 0.0)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must be latched True after valid press in GREEN (FR-007)")

    def test_FR007_cr_pending_survives_into_yellow(self):
        """CR_PENDING remains True after transitioning from GREEN to YELLOW."""
        sm, gpio = _make_sm()
        # Press early in GREEN.
        sm.update(True, 0.0)
        self.assertTrue(sm.cr_pending)

        # Advance through GREEN → YELLOW.
        n = ticks_for_ms(DURATION_GREEN_MS) + 5
        for i in range(1, n):
            sm.update(False, i * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S2_YELLOW)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must survive through GREEN→YELLOW (FR-014)")

    def test_FR007_cr_pending_survives_into_red(self):
        """CR_PENDING remains True after transitioning from YELLOW to RED."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)  # latch during GREEN

        n = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 10
        for i in range(1, n):
            sm.update(False, i * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S3_RED)
        self.assertTrue(sm.cr_pending,
                        "CR_PENDING must survive through YELLOW→RED (FR-014)")


class TestFR008PedWalkInsertedAfterRed(unittest.TestCase):
    """FR-008, FR-014: after GREEN press, PEDESTRIAN WALK is inserted after RED."""

    def _run_full_cr_cycle(self):
        """Run through GREEN(+CR) → YELLOW → RED → S4_PED and return (sm, gpio)."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)           # press during first tick of GREEN
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(total_ms) + 10
        for i in range(1, n):
            sm.update(False, i * TICK_MS)
        return sm, gpio

    def test_FR008_state_sequence_green_yellow_red_ped(self):
        """State order with CR during GREEN must be S1→S2→S3→S4."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)  # CR during GREEN
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(total_ms) + 15

        state_sequence = []
        prev = PhaseState.S1_GREEN
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s != prev:
                state_sequence.append(s)
                prev = s

        self.assertIn(PhaseState.S2_YELLOW, state_sequence, "S2_YELLOW must appear")
        self.assertIn(PhaseState.S3_RED,    state_sequence, "S3_RED must appear")
        self.assertIn(PhaseState.S4_PED,    state_sequence,
                      "S4_PED must follow S3_RED when CR was latched (FR-008)")

        # Ordering: the index of each must be strictly increasing.
        idx = {s: state_sequence.index(s)
               for s in [PhaseState.S2_YELLOW, PhaseState.S3_RED, PhaseState.S4_PED]}
        self.assertLess(idx[PhaseState.S2_YELLOW], idx[PhaseState.S3_RED])
        self.assertLess(idx[PhaseState.S3_RED],    idx[PhaseState.S4_PED])

    def test_FR008_ped_walk_gpio_is_red_only(self):
        """During S4_PED the gpio_set_leds call must be (True, False, False)."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)
        total_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(total_ms) + 15
        prev = PhaseState.S1_GREEN
        ped_gpio_call = None
        for i in range(1, n):
            t = i * TICK_MS
            s = sm.update(False, t)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                ped_gpio_call = gpio.led_calls[-1]
                break
            prev = s
        self.assertIsNotNone(ped_gpio_call, "S4_PED must be entered")
        red, yellow, green = ped_gpio_call
        self.assertTrue(red,     "GPIO17 must be HIGH in S4_PED (FR-008)")
        self.assertFalse(yellow, "GPIO27 must be LOW in S4_PED")
        self.assertFalse(green,  "GPIO22 must be LOW in S4_PED")

    def test_FR008_ped_walk_duration_honored(self):
        """S4_PED must last at least DURATION_PED_MS - tick tolerance."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)

        # Advance through GREEN+YELLOW+RED to reach S4_PED entry.
        lead_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n_lead = ticks_for_ms(lead_ms) + 15
        ped_entry_tick = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n_lead):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                ped_entry_tick = i
                break
            prev = s

        self.assertIsNotNone(ped_entry_tick, "S4_PED was never entered")

        # From S4_PED entry, count how many ticks until we exit.
        TOLERANCE_MS = 200
        max_ped_ticks = ticks_for_ms(DURATION_PED_MS + TOLERANCE_MS)
        min_ped_ticks = ticks_for_ms(DURATION_PED_MS - TOLERANCE_MS)

        ped_duration_ticks = 0
        for j in range(max_ped_ticks + 10):
            t = (ped_entry_tick + j) * TICK_MS
            s = sm.update(False, t)
            if s != PhaseState.S4_PED:
                break
            ped_duration_ticks += 1

        ped_duration_ms = ped_duration_ticks * TICK_MS
        self.assertGreaterEqual(ped_duration_ms, DURATION_PED_MS - TOLERANCE_MS,
                                f"PED WALK too short: {ped_duration_ms} ms (FR-008/NF-004)")
        self.assertLessEqual(ped_duration_ms, DURATION_PED_MS + TOLERANCE_MS,
                             f"PED WALK too long: {ped_duration_ms} ms (FR-008/NF-004)")

    def test_FR014_green_phase_not_shortened_by_cr(self):
        """GREEN phase must run its full duration even after CR is latched (FR-014)."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)  # CR at tick 0

        # Confirm still in GREEN after only half the duration.
        half = DURATION_GREEN_MS // 2
        for i in range(1, ticks_for_ms(half)):
            sm.update(False, i * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN,
                         "GREEN must not be cut short after CR latch (FR-014)")


class TestFR010CRClearedAfterPedWalk(unittest.TestCase):
    """FR-010: CR_PENDING cleared after S4_PED; normal cycling resumes."""

    def test_FR010_cr_pending_false_after_ped_walk_exits(self):
        """CR_PENDING must be False once S4_PED transitions to S1_GREEN."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)

        total_ms = (DURATION_GREEN_MS + DURATION_YELLOW_MS
                    + DURATION_RED_MS + DURATION_PED_MS)
        n = ticks_for_ms(total_ms) + 20
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S1_GREEN and i > ticks_for_ms(DURATION_GREEN_MS) + 5:
                # We've cycled back to GREEN after PED walk.
                break

        self.assertFalse(sm.cr_pending,
                         "CR_PENDING must be cleared when S4_PED exits (FR-010)")

    def test_FR010_green_resumes_after_ped_walk_no_second_walk(self):
        """After PED walk the system must not insert a second PED walk."""
        sm, gpio = _make_sm()
        sm.update(True, 0.0)  # one CR during GREEN

        # Drive through two full cycles (first with PED, second without).
        total_ms = (DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
                    + DURATION_PED_MS + DURATION_GREEN_MS + DURATION_YELLOW_MS
                    + DURATION_RED_MS)
        n = ticks_for_ms(total_ms) + 30
        s4_count = 0
        prev = None
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 1,
                         "Exactly one S4_PED must occur after a single CR (FR-010/FR-013)")


if __name__ == "__main__":
    unittest.main()
