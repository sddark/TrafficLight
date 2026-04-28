---
name: TLC project documentation context
description: Key facts about the Bench Test Traffic Light Controller project needed to write accurate wiki documentation
type: project
---

The TLC project is a Raspberry Pi bench prototype implementing a 4-phase traffic light FSM with a crosswalk request button. Document IDs: SYS-TLC-001 (spec) and ARCH-TLC-001 (architecture).

**Requirement counts:** 20 FRs, 10 NFRs, 5 constraints (C-001–C-005).

**Test suite:** 108 tests in `tests/`, named by requirement ID (e.g., `test_FR018_FR020_debounce.py`). GPIO mocked via `sys.modules` injection in `tests/test_helpers.py`. Runs on any OS without hardware.

**GPIO pin assignments (BCM):** GPIO 17 = Red LED, GPIO 27 = Yellow LED, GPIO 22 = Green LED, GPIO 18 = CRB input (active-low, internal pull-up).

**Phase durations:** GREEN 7000 ms, YELLOW 3000 ms, RED 7000 ms, PEDESTRIAN WALK 10000 ms.

**Debounce:** 50 ms stability window (FR-019) + 300 ms post-press lockout (FR-020). Two-path emit: held-path and release-path, both at 50 ms from press start.

**Key FR-010 note:** cr_pending is cleared on entry to S4_PED (S3_RED → S4_PED transition), not on exit. This was a spec discrepancy caught during implementation and corrected in the spec and architecture.

**Docs written:** `Docs/quick-start-guide.md` and `Docs/system-summary.md` created 2026-04-26.

**Why:** Demonstration and learning platform for V-model embedded software development. Not a safety-critical system.

**How to apply:** Use these facts when writing or updating any TLC documentation. Verify counts (108 tests, 20 FRs) against source if in doubt.
