#!/usr/bin/env python3
# =============================================================================
# run_all_tests.py
# Document reference: ARCH-TLC-001
# Purpose: Discover and run all TLC integration tests in the tests/ directory.
#          Produces a pass/fail summary and exits with code 0 (all pass) or
#          code 1 (any failure or error).
#
# Usage:
#   python tests/run_all_tests.py              # from project root
#   python -m pytest tests/                   # pytest-compatible alternative
# =============================================================================

import sys
import os
import unittest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so 'import tlc.*' resolves correctly
# regardless of how this script is invoked.
# ---------------------------------------------------------------------------
_SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Discover all test modules in the tests/ package.
# The discovery starts from the tests/ directory and loads any file matching
# test_*.py.  test_helpers.py is excluded by the pattern automatically.
# ---------------------------------------------------------------------------

loader = unittest.TestLoader()
suite  = loader.discover(
    start_dir=_SCRIPT_DIR,
    pattern="test_*.py",
    top_level_dir=_PROJECT_ROOT,
)


def _count_tests(suite: unittest.TestSuite) -> int:
    count = 0
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            count += _count_tests(item)
        else:
            count += 1
    return count


def main() -> int:
    discovered = _count_tests(suite)
    print(f"{'=' * 70}")
    print(f"  TLC Integration Test Suite — ARCH-TLC-001")
    print(f"{'=' * 70}")
    print(f"  Discovered {discovered} test(s) across {_SCRIPT_DIR}")
    print(f"{'=' * 70}\n")

    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        failfast=False,
    )
    result = runner.run(suite)

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Tests run   : {result.testsRun}")
    print(f"  Errors      : {len(result.errors)}")
    print(f"  Failures    : {len(result.failures)}")
    print(f"  Skipped     : {len(result.skipped)}")

    if result.wasSuccessful():
        print(f"\n  RESULT: PASS — all tests passed.")
        print(f"{'=' * 70}")
        return 0
    else:
        print(f"\n  RESULT: FAIL — {len(result.errors)} error(s), "
              f"{len(result.failures)} failure(s).")
        print(f"{'=' * 70}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
