# =============================================================================
# tlc/main.py
# Document reference: ARCH-TLC-001
#
# Responsibilities:
#   - Entry point for the Traffic Light Controller application.
#   - Orchestrate startup sequence: GPIO initialisation, debounce construction,
#     state machine construction and initialisation (FR-016, FR-017).
#   - Run the 10 ms tick loop that polls the CRB, debounces the raw signal, and
#     advances the state machine (FR-001, FR-006, NF-005).
#   - Catch RuntimeError from the state machine's error handler (C-004) and
#     terminate the process with exit code 1.
#   - Guarantee GPIO cleanup on all exit paths via a finally block (NF-007).
#
# Assumptions:
#   - This module is executed as __main__ on the Raspberry Pi.
#   - tlc.gpio_driver provides the real GPIO interface; MockGPIODriver is used
#     only during unit tests (tests never import this module directly).
# =============================================================================

import sys
import time

from tlc.timing import now_ms, TICK_PERIOD_S
from tlc import gpio_driver
from tlc.debounce import DebounceModule
from tlc.state_machine import StateMachine


def main() -> None:
    """
    Top-level TLC application entry point.

    Initialises hardware, enters the perpetual 10 ms tick loop, and handles
    clean shutdown on both normal termination and fault conditions.
    """
    gpio_driver.gpio_init()          # FR-017: configure all pins; LEDs initialise LOW
    t0_startup_ms = now_ms()

    debounce_filter = DebounceModule()   # FR-018, FR-019, FR-020
    traffic_light_sm = StateMachine(gpio_driver)

    t1_before_green_ms = now_ms()
    traffic_light_sm.initialize(t1_before_green_ms)   # FR-016: enter GREEN; FR-017: green ON

    # FR-017: all-off window must be < 500 ms; log a warning if it is exceeded
    milliseconds_elapsed_from_init_to_green = t1_before_green_ms - t0_startup_ms
    if milliseconds_elapsed_from_init_to_green >= 500.0:
        print(
            "[WARN] Startup exceeded 500 ms — FR-017 may be violated",
            flush=True,
        )

    try:
        while True:                                              # FR-001: continuous cycling
            tick_start_ms = now_ms()

            raw_crb_pressed = gpio_driver.gpio_read_crb()       # FR-006: monitor CRB at all times
            valid_press_confirmed = debounce_filter.process(    # FR-018–FR-020: debounce filter
                raw_crb_pressed, tick_start_ms
            )
            traffic_light_sm.update(                            # NF-005: transition latency ≤ 50 ms
                valid_press_confirmed, tick_start_ms
            )

            # Sleep for the remainder of the 10 ms tick period (NF-005)
            tick_elapsed_seconds = (now_ms() - tick_start_ms) / 1000.0
            remaining_sleep_seconds = max(0.0, TICK_PERIOD_S - tick_elapsed_seconds)
            time.sleep(remaining_sleep_seconds)

    except RuntimeError as fault_error:
        # C-004: enter_error_state() has already illuminated red-only GPIO;
        # log the fault message and exit with a non-zero code.
        print(f"[FATAL] {fault_error}", flush=True)
        sys.exit(1)

    except KeyboardInterrupt:
        # User pressed Ctrl+C — clean exit
        print("\n[INFO] Shutdown requested", flush=True)

    finally:
        gpio_driver.gpio_cleanup()   # NF-007: safe GPIO release on all exit paths


if __name__ == "__main__":
    main()
