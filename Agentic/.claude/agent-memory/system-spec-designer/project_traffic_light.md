---
name: Traffic Light Bench Prototype Project
description: Single-intersection bench prototype; SRS-TLC-001 v1.1 (2026-04-28) is the current requirements authority; states renamed GO/YIELD/STOP/PEDESTRIAN; input renamed PRS; implementation-neutral language throughout
type: project
---

System specification written 2026-04-26 for the bench test traffic light controller.

**Why:** User wants a formal, implementation-agnostic spec to drive downstream code and test agents in the multi-agent workflow.

**How to apply:** The primary requirements authority is `Docs/SRS-TLC-001.md` (SRS-TLC-001 v1.1, Released 2026-04-28), which supersedes SYS-TLC-001 v1.0. SRS-TLC-001 follows IEEE 29148-2018 structure. The original system spec at `Docs/system-specification.md` (SYS-TLC-001) is retained as a historical artifact. The architecture is in `Docs/system-architecture.md` (ARCH-TLC-001 v1.0). All behavioral, timing, and interface decisions should trace back to SRS-TLC-001 v1.1.

Key design decisions as of v1.1 (implementation-neutral language):
- Four states: GO, YIELD, STOP, PEDESTRIAN
- Nominal timing: 7s GO, 3s YIELD, 7s STOP, 10s PEDESTRIAN
- Crosswalk request latches on valid PRS activation; serviced after STOP phase completes; ignored during PEDESTRIAN phase
- Debounce: 50 ms stability threshold, 300 ms post-activation lockout
- PEDESTRIAN phase shares the STOP indicator (no separate pedestrian indicator in this prototype)
- Power-on defaults to GO phase; CR lost on power interruption
- Only SHALL requirements remain; SHOULD and MAY removed entirely
- Input renamed from Crosswalk Request Button (CRB) to Pedestrian Request Signal (PRS)
- Indicator states described as active/inactive (not illuminated/on/off)
- No color names (red/yellow/green) appear anywhere in the document

Open questions OQ-001 through OQ-005 are all resolved (closed) in ARCH-TLC-001 v1.0. Resolution notes are preserved in SRS-TLC-001 Appendix B.
