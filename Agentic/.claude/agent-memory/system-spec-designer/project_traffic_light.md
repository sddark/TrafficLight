---
name: Traffic Light Bench Prototype Project
description: Single-intersection bench prototype with 3 LED indicators and 1 crosswalk pushbutton; system spec written 2026-04-26 as SYS-TLC-001 v1.0
type: project
---

System specification written 2026-04-26 for the bench test traffic light controller.

**Why:** User wants a formal, implementation-agnostic spec to drive downstream code and test agents in the multi-agent workflow.

**How to apply:** When the code-writer or test-writer agents reference the spec, point them to `Docs/system-specification.md` (document ID SYS-TLC-001). All behavioral, timing, and interface decisions should trace back to that document.

Key design decisions captured in the spec:
- Four states: GREEN, YELLOW, RED, PEDESTRIAN WALK
- Nominal timing: 7s GREEN, 3s YELLOW, 7s RED, 10s PEDESTRIAN WALK
- Crosswalk request latches on valid press; serviced after RED phase completes; ignored during PEDESTRIAN WALK
- Debounce: 50 ms stability threshold, 300 ms post-press lockout
- PEDESTRIAN WALK uses the red indicator (no separate pedestrian indicator in this prototype)
- Power-on defaults to GREEN; CR lost on power interruption

Five open questions flagged for stakeholder input (OQ-001 through OQ-005), including: blinking countdown in walk phase, operator reset button, whether CR during walk phase should queue, duration tuning, and CR acknowledgment indicator.
