---
name: User Profile — TLC Project
description: Role and working style of the user on the Traffic Light Controller project
type: user
---

The user is an engineer building a Raspberry Pi bench-test traffic light controller as a hardware demonstration and learning platform. They work with a formal architecture document (ARCH-TLC-001) and a system specification (SYS-TLC-001) and want tests written against those contracts before implementation exists.

The user values:
- Strict one-requirement-group-per-file test organization
- Requirement IDs embedded in test method names (e.g., test_FR001_...)
- Tests runnable on Windows without hardware (full RPi.GPIO mocking)
- Standard library only (unittest), no external test framework required
- Deterministic time control via simulated ticks (no real wall-clock dependency)
