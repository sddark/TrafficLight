import time

# NF-005: 10 ms tick period yields worst-case transition latency < 18 ms (well within 50 ms limit)
TICK_PERIOD_MS = 10
TICK_PERIOD_S  = 0.010

# NF-001: GREEN phase nominal 7 s, range 5–10 s
DURATION_GREEN_MS  = 7000
# NF-002: YELLOW phase 3 s ± 100 ms
DURATION_YELLOW_MS = 3000
# NF-003: RED phase nominal 7 s, range 5–10 s
DURATION_RED_MS    = 7000
# NF-004: PEDESTRIAN WALK phase 10 s ± 200 ms
DURATION_PED_MS    = 10000

# FR-019: reject CRB transitions stable < 50 ms
DEBOUNCE_STABLE_MS  = 50
# FR-020: 300 ms post-press lockout after each valid press
DEBOUNCE_LOCKOUT_MS = 300


def now_ms() -> float:
    # NF-008: time.monotonic() is immune to NTP/DST adjustments; no drift accumulation
    return time.monotonic() * 1000.0


def elapsed_ms(start_ms: float) -> float:
    return now_ms() - start_ms
