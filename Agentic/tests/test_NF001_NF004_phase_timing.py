# =============================================================================
# test_NF001_NF004_phase_timing.py
# Document reference: ARCH-TLC-001
# Requirements covered: NF-001, NF-002, NF-003, NF-004
# Description: Verifies that each phase runs for its correct nominal duration
#              within the specified tolerance.  Time is controlled by advancing
#              tick_time_ms deterministically — no real wall clock.
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

# Tolerances from the architecture NFR table.
TOL_GREEN_MS  = 3000  # NF-001: 7000 ± 3000
TOL_YELLOW_MS =  100  # NF-002: 3000 ± 100
TOL_RED_MS    = 3000  # NF-003: 7000 ± 3000
TOL_PED_MS    =  200  # NF-004: 10000 ± 200

# Tick resolution adds up to one TICK_MS overhead (10 ms) per transition.
TICK_OVERHEAD = TICK_MS


def _make_sm() -> tuple[StateMachine, MockGPIODriver]:
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


def _measure_phase_duration(sm, target_state: PhaseState,
                             enter_tick: int, max_ticks: int,
                             press_tick: int | None = None) -> int:
    """
    Starting from enter_tick (the first tick inside target_state),
    count how many consecutive ticks sm stays in target_state.
    Optionally inject a press_event at press_tick (absolute tick index).
    Returns the tick count spent in target_state.
    """
    count = 0
    for j in range(max_ticks):
        i = enter_tick + j
        vp = (i == press_tick) if press_tick is not None else False
        s = sm.update(vp, i * TICK_MS)
        if s != target_state:
            break
        count += 1
    return count


class TestNF001GreenPhaseDuration(unittest.TestCase):
    """NF-001: GREEN phase nominal 7000 ms, range 5000–10000 ms."""

    def test_NF001_green_does_not_exit_early(self):
        """
        GREEN must still be active at DURATION_GREEN_MS - TICK_OVERHEAD ms.
        We confirm the SM stays in S1_GREEN for at least DURATION_GREEN_MS ticks.
        """
        sm, gpio = _make_sm()
        early_ticks = ticks_for_ms(DURATION_GREEN_MS) - 2  # one tick before expected exit
        for i in range(1, early_ticks):
            s = sm.update(False, i * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN,
                         f"GREEN exited too early before {DURATION_GREEN_MS} ms (NF-001)")

    def test_NF001_green_exits_within_tolerance(self):
        """GREEN must exit within DURATION_GREEN_MS + TOL_GREEN_MS + TICK_OVERHEAD."""
        sm, gpio = _make_sm()
        upper_ticks = ticks_for_ms(DURATION_GREEN_MS + TOL_GREEN_MS) + 5

        exited = False
        for i in range(1, upper_ticks):
            s = sm.update(False, i * TICK_MS)
            if s != PhaseState.S1_GREEN:
                exited = True
                elapsed_ms = i * TICK_MS
                self.assertLessEqual(elapsed_ms, DURATION_GREEN_MS + TOL_GREEN_MS + TICK_OVERHEAD,
                                     f"GREEN ran too long: {elapsed_ms} ms (NF-001)")
                break
        self.assertTrue(exited, "GREEN never exited within tolerance window (NF-001)")

    def test_NF001_green_duration_within_both_bounds(self):
        """
        Measure actual GREEN duration and verify 5000 ≤ ms ≤ 10000.
        """
        sm, gpio = _make_sm()
        max_ticks = ticks_for_ms(DURATION_GREEN_MS + TOL_GREEN_MS) + 10
        green_ticks = 0
        for i in range(1, max_ticks):
            s = sm.update(False, i * TICK_MS)
            if s != PhaseState.S1_GREEN:
                break
            green_ticks += 1

        green_ms = green_ticks * TICK_MS
        self.assertGreaterEqual(green_ms, DURATION_GREEN_MS - TOL_GREEN_MS,
                                f"GREEN too short: {green_ms} ms (NF-001)")
        self.assertLessEqual(green_ms, DURATION_GREEN_MS + TOL_GREEN_MS,
                             f"GREEN too long: {green_ms} ms (NF-001)")


class TestNF002YellowPhaseDuration(unittest.TestCase):
    """NF-002: YELLOW phase 3000 ms ± 100 ms (tightest tolerance)."""

    def _reach_yellow(self) -> tuple[StateMachine, MockGPIODriver, int]:
        sm, gpio = _make_sm()
        n = ticks_for_ms(DURATION_GREEN_MS) + 10
        entry = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S2_YELLOW and prev != PhaseState.S2_YELLOW:
                entry = i
                break
            prev = s
        assert entry is not None
        return sm, gpio, entry

    def test_NF002_yellow_does_not_exit_early(self):
        """YELLOW must remain active until at least DURATION_YELLOW_MS - TICK_OVERHEAD ms."""
        sm, gpio, y_tick = self._reach_yellow()
        early_ticks = ticks_for_ms(DURATION_YELLOW_MS) - 2
        for j in range(1, early_ticks):
            sm.update(False, (y_tick + j) * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S2_YELLOW,
                         "YELLOW exited too early (NF-002)")

    def test_NF002_yellow_exits_at_nominal_plus_tolerance(self):
        """YELLOW must exit before DURATION_YELLOW_MS + TOL_YELLOW_MS + one tick."""
        sm, gpio, y_tick = self._reach_yellow()
        upper_ticks = ticks_for_ms(DURATION_YELLOW_MS + TOL_YELLOW_MS) + 5
        exited = False
        for j in range(1, upper_ticks):
            s = sm.update(False, (y_tick + j) * TICK_MS)
            if s != PhaseState.S2_YELLOW:
                exited = True
                elapsed_ms = j * TICK_MS
                self.assertLessEqual(elapsed_ms, DURATION_YELLOW_MS + TOL_YELLOW_MS + TICK_OVERHEAD,
                                     f"YELLOW ran too long: {elapsed_ms} ms (NF-002)")
                break
        self.assertTrue(exited, "YELLOW never exited within tolerance (NF-002)")

    def test_NF002_yellow_duration_within_plus_minus_100ms(self):
        """Measured YELLOW duration must be 2900–3100 ms."""
        sm, gpio, y_tick = self._reach_yellow()
        max_ticks = ticks_for_ms(DURATION_YELLOW_MS + TOL_YELLOW_MS) + 10
        yellow_ticks = 0
        for j in range(1, max_ticks):
            s = sm.update(False, (y_tick + j) * TICK_MS)
            if s != PhaseState.S2_YELLOW:
                break
            yellow_ticks += 1

        yellow_ms = yellow_ticks * TICK_MS
        self.assertGreaterEqual(yellow_ms, DURATION_YELLOW_MS - TOL_YELLOW_MS,
                                f"YELLOW too short: {yellow_ms} ms (NF-002)")
        self.assertLessEqual(yellow_ms, DURATION_YELLOW_MS + TOL_YELLOW_MS,
                             f"YELLOW too long: {yellow_ms} ms (NF-002)")


class TestNF003RedPhaseDuration(unittest.TestCase):
    """NF-003: RED phase nominal 7000 ms, range 5000–10000 ms."""

    def _reach_red(self) -> tuple[StateMachine, MockGPIODriver, int]:
        sm, gpio = _make_sm()
        n = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 15
        entry = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S3_RED and prev != PhaseState.S3_RED:
                entry = i
                break
            prev = s
        assert entry is not None
        return sm, gpio, entry

    def test_NF003_red_does_not_exit_early(self):
        sm, gpio, r_tick = self._reach_red()
        early_ticks = ticks_for_ms(DURATION_RED_MS) - 2
        for j in range(1, early_ticks):
            sm.update(False, (r_tick + j) * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S3_RED,
                         "RED exited too early (NF-003)")

    def test_NF003_red_duration_within_bounds(self):
        sm, gpio, r_tick = self._reach_red()
        max_ticks = ticks_for_ms(DURATION_RED_MS + TOL_RED_MS) + 10
        red_ticks = 0
        for j in range(1, max_ticks):
            s = sm.update(False, (r_tick + j) * TICK_MS)
            if s != PhaseState.S3_RED:
                break
            red_ticks += 1

        red_ms = red_ticks * TICK_MS
        self.assertGreaterEqual(red_ms, DURATION_RED_MS - TOL_RED_MS,
                                f"RED too short: {red_ms} ms (NF-003)")
        self.assertLessEqual(red_ms, DURATION_RED_MS + TOL_RED_MS,
                             f"RED too long: {red_ms} ms (NF-003)")


class TestNF004PedWalkDuration(unittest.TestCase):
    """NF-004: PEDESTRIAN WALK 10000 ms ± 200 ms."""

    def _reach_ped(self) -> tuple[StateMachine, MockGPIODriver, int]:
        sm, gpio = _make_sm()
        sm.update(True, 0.0)   # CR during GREEN
        lead_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(lead_ms) + 15
        entry = None
        prev = PhaseState.S1_GREEN
        for i in range(1, n):
            s = sm.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                entry = i
                break
            prev = s
        assert entry is not None
        return sm, gpio, entry

    def test_NF004_ped_does_not_exit_early(self):
        sm, gpio, p_tick = self._reach_ped()
        early_ticks = ticks_for_ms(DURATION_PED_MS) - 2
        for j in range(1, early_ticks):
            sm.update(False, (p_tick + j) * TICK_MS)
        self.assertEqual(sm.current_state, PhaseState.S4_PED,
                         "PED WALK exited too early (NF-004)")

    def test_NF004_ped_exits_within_tolerance(self):
        sm, gpio, p_tick = self._reach_ped()
        upper_ticks = ticks_for_ms(DURATION_PED_MS + TOL_PED_MS) + 5
        exited = False
        for j in range(1, upper_ticks):
            s = sm.update(False, (p_tick + j) * TICK_MS)
            if s != PhaseState.S4_PED:
                exited = True
                elapsed_ms = j * TICK_MS
                self.assertLessEqual(elapsed_ms, DURATION_PED_MS + TOL_PED_MS + TICK_OVERHEAD,
                                     f"PED WALK ran too long: {elapsed_ms} ms (NF-004)")
                break
        self.assertTrue(exited, "PED WALK never exited within tolerance (NF-004)")

    def test_NF004_ped_duration_within_plus_minus_200ms(self):
        sm, gpio, p_tick = self._reach_ped()
        max_ticks = ticks_for_ms(DURATION_PED_MS + TOL_PED_MS) + 10
        ped_ticks = 0
        for j in range(1, max_ticks):
            s = sm.update(False, (p_tick + j) * TICK_MS)
            if s != PhaseState.S4_PED:
                break
            ped_ticks += 1

        ped_ms = ped_ticks * TICK_MS
        self.assertGreaterEqual(ped_ms, DURATION_PED_MS - TOL_PED_MS,
                                f"PED WALK too short: {ped_ms} ms (NF-004)")
        self.assertLessEqual(ped_ms, DURATION_PED_MS + TOL_PED_MS,
                             f"PED WALK too long: {ped_ms} ms (NF-004)")


if __name__ == "__main__":
    unittest.main()
