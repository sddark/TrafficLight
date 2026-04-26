# =============================================================================
# test_NF007_power_recovery.py
# Document reference: ARCH-TLC-001
# Requirements covered: NF-007, Edge Case F
# Description: Simulates a power cycle by re-constructing the StateMachine.
#              Verifies that the new instance starts in S1_GREEN with
#              CR_PENDING=False regardless of what state the previous instance
#              was in, confirming that no persistent state survives a power cycle.
# =============================================================================

import tests.test_helpers as helpers  # noqa: F401

import unittest

from tlc.state_machine import StateMachine, PhaseState
from tests.test_helpers import (
    MockGPIODriver,
    DURATION_GREEN_MS,
    DURATION_YELLOW_MS,
    DURATION_RED_MS,
    TICK_MS,
    ticks_for_ms,
)


def _make_and_init_sm() -> tuple[StateMachine, MockGPIODriver]:
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


def _simulate_power_cycle() -> tuple[StateMachine, MockGPIODriver]:
    """
    Simulates a power cycle: construct and return a brand-new SM instance.
    In production this is equivalent to power-on; the old instance is discarded.
    """
    gpio = MockGPIODriver()
    sm = StateMachine(gpio)
    sm.initialize(tick_time_ms=0.0)
    return sm, gpio


class TestNF007PowerCycleStartsGreenNoCR(unittest.TestCase):
    """NF-007: resume from GREEN with CR_PENDING=False after any power cycle."""

    def test_NF007_fresh_instance_starts_in_green(self):
        """A newly constructed StateMachine must be in S1_GREEN (FR-016)."""
        sm, gpio = _simulate_power_cycle()
        self.assertEqual(sm.current_state, PhaseState.S1_GREEN,
                         "Re-initialized SM must start in S1_GREEN (NF-007)")

    def test_NF007_fresh_instance_cr_pending_false(self):
        """CR_PENDING must be False on a fresh instance (Edge Case F)."""
        sm, gpio = _simulate_power_cycle()
        self.assertFalse(sm.cr_pending,
                         "CR_PENDING must be False after power cycle (NF-007, Edge Case F)")

    def test_NF007_power_cycle_during_yellow_with_cr_pending(self):
        """
        Edge Case F: CR pending, system in YELLOW → power cycle →
        new instance must have no CR and be in GREEN.
        """
        # Build and run first instance into YELLOW with CR pending.
        sm1, gpio1 = _make_and_init_sm()
        sm1.update(True, 0.0)   # latch CR during GREEN
        n_green = ticks_for_ms(DURATION_GREEN_MS) + 5
        for i in range(1, n_green):
            sm1.update(False, i * TICK_MS)
        self.assertEqual(sm1.current_state, PhaseState.S2_YELLOW)
        self.assertTrue(sm1.cr_pending)

        # Power cycle — construct fresh instance.
        sm2, gpio2 = _simulate_power_cycle()
        self.assertEqual(sm2.current_state, PhaseState.S1_GREEN,
                         "After power cycle from YELLOW, must resume GREEN (NF-007)")
        self.assertFalse(sm2.cr_pending,
                         "CR_PENDING must be lost on power cycle (Edge Case F)")

    def test_NF007_power_cycle_during_red_with_cr_pending(self):
        """Power cycle from RED with CR pending → new instance in GREEN, no CR."""
        sm1, gpio1 = _make_and_init_sm()
        sm1.update(True, 0.0)
        total = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS) + 15
        for i in range(1, total):
            sm1.update(False, i * TICK_MS)
        self.assertEqual(sm1.current_state, PhaseState.S3_RED)
        self.assertTrue(sm1.cr_pending)

        sm2, gpio2 = _simulate_power_cycle()
        self.assertEqual(sm2.current_state, PhaseState.S1_GREEN)
        self.assertFalse(sm2.cr_pending)

    def test_NF007_power_cycle_during_ped_walk(self):
        """Power cycle from S4_PED → new instance in GREEN, no CR."""
        sm1, gpio1 = _make_and_init_sm()
        sm1.update(True, 0.0)
        total = ticks_for_ms(DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS) + 15
        for i in range(1, total):
            sm1.update(False, i * TICK_MS)
        self.assertEqual(sm1.current_state, PhaseState.S4_PED)

        sm2, gpio2 = _simulate_power_cycle()
        self.assertEqual(sm2.current_state, PhaseState.S1_GREEN)
        self.assertFalse(sm2.cr_pending)

    def test_NF007_post_power_cycle_normal_cycle_no_ped_walk(self):
        """
        After power cycling from a state where CR was pending, the new instance
        must run a plain GREEN→YELLOW→RED→GREEN cycle with no S4_PED.
        """
        sm1, gpio1 = _make_and_init_sm()
        sm1.update(True, 0.0)   # CR latched

        # Power cycle.
        sm2, gpio2 = _simulate_power_cycle()
        self.assertFalse(sm2.cr_pending)

        # Run a full cycle on sm2 and verify no S4_PED appears.
        cycle_ms = DURATION_GREEN_MS + DURATION_YELLOW_MS + DURATION_RED_MS
        n = ticks_for_ms(cycle_ms) + 20
        s4_count = 0
        prev = PhaseState.S1_GREEN
        for i in range(1, n):
            s = sm2.update(False, i * TICK_MS)
            if s == PhaseState.S4_PED and prev != PhaseState.S4_PED:
                s4_count += 1
            prev = s

        self.assertEqual(s4_count, 0,
                         "No S4_PED must appear after power cycle (NF-007, Edge Case F)")

    def test_NF007_repeated_power_cycles_always_start_green(self):
        """
        Multiple sequential power cycles all produce S1_GREEN with no CR.
        Simulates repeated power toggling.
        """
        for _ in range(5):
            sm, gpio = _simulate_power_cycle()
            self.assertEqual(sm.current_state, PhaseState.S1_GREEN)
            self.assertFalse(sm.cr_pending)


if __name__ == "__main__":
    unittest.main()
