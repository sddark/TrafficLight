# Bench Test Traffic Light Controller — System Specification

**Document ID:** SYS-TLC-001  
**Version:** 1.0  
**Date:** 2026-04-26  
**Status:** Draft

---

## Table of Contents

1. [Overview](#1-overview)
2. [Stakeholders and User Roles](#2-stakeholders-and-user-roles)
3. [System Scope and Boundaries](#3-system-scope-and-boundaries)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Logical Data Model](#6-logical-data-model)
7. [Interface Specifications](#7-interface-specifications)
8. [Behavioral Specifications](#8-behavioral-specifications)
9. [Constraints and Assumptions](#9-constraints-and-assumptions)
10. [Open Questions](#10-open-questions)
11. [Glossary](#11-glossary)

---

## 1. Overview

### 1.1 Purpose

This document specifies the required behavior of a bench-prototype Traffic Light Controller (TLC). The TLC simulates a single-lane, single-intersection traffic signal with an integrated pedestrian crosswalk request capability. It is intended for use as a hardware demonstration and learning platform assembled on a breadboard or equivalent development surface.

### 1.2 Goals

- Provide a continuously cycling traffic signal with well-defined timing for each phase.
- Allow a pedestrian to request a walk interval by pressing a button, with the request honored at the next safe opportunity.
- Serve as a self-contained, observable system whose behavior can be fully verified through visual inspection of the indicator outputs and a stopwatch.

### 1.3 Context

The system is a bench prototype, not a safety-critical production installation. Timing values and behavioral rules are chosen to be practical for demonstration and testing at a lab bench. All observable outputs are produced by three discrete light indicators.

---

## 2. Stakeholders and User Roles

| Role | Description | Interaction with System |
|------|-------------|------------------------|
| Lab Operator | The engineer or student assembling and verifying the prototype | Powers the system on/off; observes indicator states; validates timing against this specification |
| Simulated Driver | The role representing vehicle traffic in the scenario | Observes red, yellow, and green indicators to determine right-of-way |
| Simulated Pedestrian | The role representing a crosswalk requester | Presses the Crosswalk Request Button to request a walk interval |

---

## 3. System Scope and Boundaries

### 3.1 In Scope

- Control of three discrete light indicators (red, yellow, green) representing the vehicle signal.
- Detection and debouncing of a single Crosswalk Request Button (CRB) input.
- A pedestrian walk phase indicated by the red light indicator.
- The full state machine governing all phase transitions and timing.

### 3.2 Out of Scope

- Multiple intersections or coordinated signal networks.
- A dedicated pedestrian WALK / DON'T WALK indicator (the red vehicle indicator doubles as the walk signal in this prototype).
- Vehicle detection sensors.
- Remote or networked control.
- Audible signals or accessibility outputs.
- Emergency vehicle preemption.
- Fault detection, diagnostics, or self-test modes.

---

## 4. Functional Requirements

### 4.1 Normal Cycling

**FR-001** — The system SHALL continuously cycle through the following phases in the following order when no crosswalk request is pending:

> GREEN → YELLOW → RED → GREEN → (repeat)

**FR-002** — During the GREEN phase, only the green indicator SHALL be illuminated; the red and yellow indicators SHALL be off.

**FR-003** — During the YELLOW phase, only the yellow indicator SHALL be illuminated; the red and green indicators SHALL be off.

**FR-004** — During the RED phase, only the red indicator SHALL be illuminated; the green and yellow indicators SHALL be off.

**FR-005** — The system SHALL illuminate exactly one indicator at a time during normal cycling. No two indicators SHALL be simultaneously illuminated, and no indicator SHALL be dark when the system is in steady-state (non-transitioning).

### 4.2 Crosswalk Request

**FR-006** — The system SHALL monitor the Crosswalk Request Button (CRB) at all times, including during phase transitions.

**FR-007** — A single press of the CRB SHALL register a Crosswalk Request (CR). The system SHALL latch this request in a pending state until it is serviced or invalidated per FR-012.

**FR-008** — The system SHALL service a pending CR by inserting a PEDESTRIAN WALK phase between the RED phase and the subsequent GREEN phase.

**FR-009** — During the PEDESTRIAN WALK phase, only the red indicator SHALL be illuminated. The green and yellow indicators SHALL be off.

**FR-010** — When the system transitions from the RED phase to the PEDESTRIAN WALK phase, the system SHALL clear the pending CR. After the PEDESTRIAN WALK phase completes, the system SHALL resume the normal cycle, beginning with the GREEN phase.

**FR-011** — If the CRB is pressed while the system is in the RED phase and no PEDESTRIAN WALK phase has yet begun for that red interval, the system SHALL insert a PEDESTRIAN WALK phase at the conclusion of the current RED phase duration (i.e., the RED phase completes its full minimum duration first, then the PEDESTRIAN WALK phase follows).

**FR-012** — If the CRB is pressed while the system is in the PEDESTRIAN WALK phase, the press SHALL be ignored. The system SHALL NOT extend the PEDESTRIAN WALK phase duration, and SHALL NOT latch an additional pending request.

**FR-013** — If the CRB is pressed multiple times before the CR is serviced, the system SHALL treat all subsequent presses as redundant. Only one PEDESTRIAN WALK phase SHALL be inserted per service cycle.

**FR-014** — If the CRB is pressed during the GREEN phase, the system SHALL latch a pending CR and SHALL service it at the end of the next RED phase (i.e., after the system completes GREEN → YELLOW → RED in full, then inserts PEDESTRIAN WALK).

**FR-015** — If the CRB is pressed during the YELLOW phase, the system SHALL latch a pending CR (if not already latched) and SHALL service it at the end of the subsequent RED phase.

### 4.3 Startup

**FR-016** — Upon power-on, the system SHALL enter the GREEN phase and begin normal cycling from that point.

**FR-017** — All indicators SHALL be off for no more than 500 milliseconds from the moment power is applied before the GREEN phase indicator illuminates.

### 4.4 Button Debounce

**FR-018** — The system SHALL debounce the CRB input such that a single physical button press, regardless of contact bounce, registers as exactly one logical press event.

**FR-019** — The system SHALL reject any CRB signal transition that does not remain stable for at least 50 milliseconds. A signal that does not meet this stability threshold SHALL NOT register as a press event.

**FR-020** — After registering one valid press event, the system SHALL suppress additional press events from the CRB for a lockout period of at least 300 milliseconds from the moment the first valid press was registered.

---

## 5. Non-Functional Requirements

### 5.1 Timing

**NF-001** — The GREEN phase SHALL have a minimum active duration of 5 seconds and a maximum active duration of 10 seconds. The nominal target is 7 seconds.

**NF-002** — The YELLOW phase SHALL have an active duration of exactly 3 seconds, with a tolerance of ±100 milliseconds.

**NF-003** — The RED phase SHALL have a minimum active duration of 5 seconds and a maximum active duration of 10 seconds. The nominal target is 7 seconds.

**NF-004** — The PEDESTRIAN WALK phase SHALL have an active duration of exactly 10 seconds, with a tolerance of ±200 milliseconds.

**NF-005** — Phase transition latency — the elapsed time between the scheduled end of one phase and the illumination of the first indicator of the next phase — SHALL not exceed 50 milliseconds.

**NF-006** — Button debounce processing SHALL complete within 100 milliseconds of the first rising edge of a qualifying press, such that no more than 100 milliseconds of additional latency is introduced between a physical press and the latching of the CR.

### 5.2 Availability

**NF-007** — The system SHALL resume normal cycling without operator intervention after any single power interruption and restoration.

**NF-008** — The system SHALL operate continuously without degradation in timing accuracy for a minimum of 8 hours of uninterrupted operation.

### 5.3 Observability

**NF-009** — All indicator state changes SHALL be visually distinguishable by a lab operator seated within 2 meters of the bench assembly under standard indoor lighting conditions.

**NF-010** — The system SHALL produce no ambiguous indicator states (e.g., partial illumination, flickering) outside of the defined transition window of 50 milliseconds.

---

## 6. Logical Data Model

### 6.1 Entities

#### System State Record

Represents the complete runtime state of the controller at any point in time.

| Attribute | Description | Possible Values |
|-----------|-------------|-----------------|
| Current Phase | The active phase the system is executing | GREEN, YELLOW, RED, PEDESTRIAN WALK |
| Phase Elapsed Time | Time elapsed since the current phase began | 0 ms to phase maximum duration |
| Crosswalk Request Pending | Whether a CR has been registered and not yet serviced | True, False |
| CRB Lockout Active | Whether the debounce lockout window is currently in effect | True, False |

#### Crosswalk Request Event

Represents a single validated button press.

| Attribute | Description |
|-----------|-------------|
| Registration Timestamp | The time at which the press was validated (debounce settled) |
| Serviced | Whether this request has been consumed by a PEDESTRIAN WALK phase |

### 6.2 Relationships

- The System State Record contains exactly one Current Phase at all times.
- At most one Crosswalk Request Event SHALL be pending at any given time.
- A Crosswalk Request Event is created upon a valid CRB press and destroyed (consumed) when the PEDESTRIAN WALK phase it triggered concludes.

---

## 7. Interface Specifications

### 7.1 Physical Inputs

#### Crosswalk Request Button (CRB)

| Property | Specification |
|----------|---------------|
| Type | Momentary contact, normally open |
| Signal levels | Two states: pressed (active) and released (inactive) |
| Minimum press duration for detection | 50 milliseconds (per FR-019) |
| Post-press lockout | 300 milliseconds minimum (per FR-020) |
| Expected contact bounce duration | Up to 20 milliseconds (system must tolerate this) |

### 7.2 Physical Outputs

#### Red Indicator

| Property | Specification |
|----------|---------------|
| Active during phases | RED, PEDESTRIAN WALK |
| Inactive during phases | GREEN, YELLOW |
| On/Off transition time | Imperceptible to human observer (target: < 5 ms) |

#### Yellow Indicator

| Property | Specification |
|----------|---------------|
| Active during phases | YELLOW |
| Inactive during phases | GREEN, RED, PEDESTRIAN WALK |
| On/Off transition time | Imperceptible to human observer (target: < 5 ms) |

#### Green Indicator

| Property | Specification |
|----------|---------------|
| Active during phases | GREEN |
| Inactive during phases | YELLOW, RED, PEDESTRIAN WALK |
| On/Off transition time | Imperceptible to human observer (target: < 5 ms) |

### 7.3 Power Interface

| Property | Specification |
|----------|---------------|
| Power source | Single external supply consistent with the development platform in use |
| Startup behavior | System enters GREEN phase within 500 ms of power application (FR-017) |
| Power loss behavior | All indicators extinguish immediately; system resets to GREEN on restoration |

---

## 8. Behavioral Specifications

### 8.1 State Machine Definition

The system operates as a deterministic finite state machine with four defined states.

#### States

| State ID | Name | Description | Active Indicator |
|----------|------|-------------|-----------------|
| S1 | GREEN | Vehicle traffic has right of way | Green |
| S2 | YELLOW | Traffic signal is transitioning; vehicles should prepare to stop | Yellow |
| S3 | RED | Vehicle traffic must stop | Red |
| S4 | PEDESTRIAN WALK | Pedestrians have right of way to cross | Red |

#### State Transition Table

| Current State | Condition | Next State |
|---------------|-----------|------------|
| S1 — GREEN | Phase duration elapsed AND no CR pending | S2 — YELLOW |
| S1 — GREEN | Phase duration elapsed AND CR pending | S2 — YELLOW |
| S2 — YELLOW | Phase duration elapsed AND no CR pending | S3 — RED |
| S2 — YELLOW | Phase duration elapsed AND CR pending | S3 — RED |
| S3 — RED | Phase duration elapsed AND no CR pending | S1 — GREEN |
| S3 — RED | Phase duration elapsed AND CR pending | S4 — PEDESTRIAN WALK |
| S4 — PEDESTRIAN WALK | Phase duration elapsed | S1 — GREEN (CR cleared) |

Note: A CR registered during S1 or S2 is carried forward through those states unchanged. It is evaluated and consumed only at the conclusion of S3.

### 8.2 Crosswalk Request Button Debounce Flow

The following scenario describes the processing of a single physical button press.

**Given** the CRB is in the released state and no lockout is active,  
**When** the CRB transitions to the pressed state,  
**Then** the system SHALL begin a stability timer of 50 milliseconds.

**Given** the stability timer is running,  
**When** the CRB remains continuously in the pressed state for 50 milliseconds,  
**Then** the system SHALL register one valid press event and activate the post-press lockout for 300 milliseconds.

**Given** the stability timer is running,  
**When** the CRB returns to the released state before 50 milliseconds have elapsed,  
**Then** the system SHALL cancel the stability timer and SHALL NOT register a press event (bounce rejection).

**Given** the post-press lockout is active,  
**When** any transition is detected on the CRB,  
**Then** the system SHALL ignore that transition and SHALL NOT start a new stability timer.

**Given** the post-press lockout is active,  
**When** 300 milliseconds have elapsed since the lockout was activated,  
**Then** the system SHALL deactivate the lockout and resume normal CRB monitoring.

### 8.3 Edge Case Scenarios

#### Edge Case A — Button Press During YELLOW Phase

**Given** the system is in S2 (YELLOW) and no CR is pending,  
**When** a valid CRB press is registered,  
**Then** the system SHALL latch a pending CR.  
**And** the YELLOW phase SHALL continue for its full duration without interruption.  
**And** the system SHALL transition to S3 (RED) upon YELLOW phase completion.  
**And** the system SHALL transition to S4 (PEDESTRIAN WALK) upon RED phase completion.

#### Edge Case B — Button Press During PEDESTRIAN WALK Phase

**Given** the system is in S4 (PEDESTRIAN WALK),  
**When** a valid CRB press is registered,  
**Then** the system SHALL ignore the press entirely.  
**And** the PEDESTRIAN WALK phase SHALL continue for its full duration.  
**And** no new CR SHALL be latched.  
**And** the subsequent cycle SHALL proceed as GREEN → YELLOW → RED without a PEDESTRIAN WALK insertion.

#### Edge Case C — Button Pressed Multiple Times Before Service

**Given** a CR is already pending,  
**When** one or more additional valid CRB presses are registered before the CR is serviced,  
**Then** each additional press SHALL be discarded.  
**And** exactly one PEDESTRIAN WALK phase SHALL be inserted when the pending CR is serviced.

#### Edge Case D — Button Press at the Instant RED Phase Begins

**Given** the system has just entered S3 (RED) within the same control cycle,  
**When** a valid CRB press is registered during S3,  
**Then** the system SHALL latch a pending CR.  
**And** the RED phase SHALL complete its full minimum duration before transitioning.  
**And** the system SHALL then transition to S4 (PEDESTRIAN WALK).

#### Edge Case E — Button Press During GREEN Phase

**Given** the system is in S1 (GREEN) and no CR is pending,  
**When** a valid CRB press is registered,  
**Then** the system SHALL latch a pending CR.  
**And** the GREEN phase SHALL continue for its remaining scheduled duration without alteration.  
**And** the system SHALL transition through S2 (YELLOW) and S3 (RED) normally.  
**And** the system SHALL insert S4 (PEDESTRIAN WALK) after S3 completes.

#### Edge Case F — Power Interruption with Pending CR

**Given** a CR is pending and the system is in any state,  
**When** power is interrupted and subsequently restored,  
**Then** the system SHALL restart in S1 (GREEN) with no pending CR.  
**And** the prior crosswalk request SHALL be considered lost; no PEDESTRIAN WALK phase SHALL be automatically inserted.

### 8.4 Timing Diagram (Nominal Cycle — No Crosswalk Request)

```
Time (seconds):    0    7   10   17   20
                   |    |    |    |    |
GREEN  [==========]
YELLOW             [====]
RED                      [=========]
GREEN                               [=======...
```

### 8.5 Timing Diagram (Nominal Cycle — Crosswalk Request During GREEN)

```
Time (seconds):    0    7   10   17   27   37
                   |    |    |    |    |    |
GREEN  [==========]
 CRB press @ t=3s (CR latched)
YELLOW             [====]
RED                      [=========]
PED WALK                             [=======]
GREEN                                          [=======...
```

---

## 9. Constraints and Assumptions

### 9.1 Constraints

**C-001** — The system is a single-intersection prototype. No multi-intersection coordination behavior is defined or implied.

**C-002** — The system has exactly three indicator outputs and exactly one button input. No additional I/O is defined.

**C-003** — The PEDESTRIAN WALK phase uses the red indicator. A separate dedicated pedestrian indicator is out of scope for this prototype (see Section 3.2).

**C-004** — The system SHALL NOT enter any undefined state. If an unspecified condition arises, the system SHALL default to illuminating only the red indicator and halting phase progression until power is cycled.

**C-005** — Timing values specified in Section 5.1 are fixed for this prototype and are not operator-configurable at runtime.

### 9.2 Assumptions

**A-001** — The power supply to the system is stable during normal operation. Voltage sags or noise on the supply line that cause behavioral anomalies are outside the scope of this specification.

**A-002** — The CRB produces a clean two-state signal. The system assumes contact bounce is confined to the first 20 milliseconds following a state transition. The 50 ms stability threshold in FR-019 provides margin above this assumption.

**A-003** — The lab environment provides consistent ambient lighting such that indicator states are visually unambiguous at a 2-meter observation distance.

**A-004** — The system operates continuously once powered. There is no sleep, standby, or low-power mode.

**A-005** — Only one person presses the CRB at a time. Simultaneous multi-person button interaction is not a considered scenario for this prototype.

---

## 10. Open Questions

**OQ-001** — Should the PEDESTRIAN WALK phase provide any visual countdown indication (e.g., a blinking red indicator in the final seconds)? This specification currently defines a static red indicator for the full walk duration. Stakeholder input is required to determine if a blink pattern is needed.

**OQ-002** — Should the system support an operator-accessible reset mechanism (e.g., a second button that restarts the cycle to GREEN) without requiring a full power cycle? Currently, no such mechanism is defined.

**OQ-003** — Should a CR registered during the PEDESTRIAN WALK phase be latched for the *next* cycle rather than discarded (per FR-012)? The current specification discards it for simplicity, but a more realistic traffic controller would queue it. Stakeholder preference is needed.

**OQ-004** — Are the nominal phase durations (7s GREEN, 3s YELLOW, 7s RED, 10s PEDESTRIAN WALK) acceptable for the intended demonstration, or should they be adjusted to better fit the lab session duration?

**OQ-005** — Should the system provide any output (e.g., a dedicated indicator LED) to signal to the pedestrian that their request has been registered and is pending? Currently, no acknowledgment output is defined.

---

## 11. Glossary

| Term | Definition |
|------|------------|
| Active Indicator | The single light indicator that is illuminated during a given phase. |
| Bench Prototype | A hardware assembly constructed on a breadboard or development surface, intended for demonstration and verification rather than production deployment. |
| Contact Bounce | The rapid, unintended on/off transitions that occur in a mechanical switch immediately after a state change, before the contacts settle. |
| CR (Crosswalk Request) | A latched internal flag indicating that a pedestrian has made a valid request for a walk interval. |
| CRB (Crosswalk Request Button) | The single momentary pushbutton input through which a pedestrian signals a walk request. |
| Debounce | The process of filtering out contact bounce so that a single physical button press registers as exactly one logical event. |
| GREEN Phase | The traffic signal phase during which the green indicator is illuminated and vehicle traffic has right of way. |
| Indicator | A discrete visual light output (red, yellow, or green) used to communicate signal state to observers. |
| Latched | A state that is retained in memory until explicitly cleared by a defined system event. |
| Nominal | The intended or target value of a parameter under standard operating conditions. |
| PEDESTRIAN WALK Phase | The traffic signal phase during which the red indicator is illuminated and pedestrians have right of way to cross. Vehicle traffic is stopped during this phase. |
| Phase | A discrete, timed operating mode of the traffic light controller, associated with a specific indicator state and a defined duration. |
| Phase Duration | The length of time the system remains in a given phase before evaluating transition conditions. |
| Post-Press Lockout | A time window following a valid button press registration during which additional CRB signals are ignored, preventing a single physical press from registering multiple times. |
| RED Phase | The traffic signal phase during which the red indicator is illuminated and vehicle traffic must stop. |
| Stability Timer | An internal timing measurement used during debounce to confirm that a button signal has held a given state for a minimum duration before the transition is accepted as valid. |
| State Machine | A behavioral model in which the system is always in exactly one of a finite set of defined states, with transitions between states governed by explicit conditions. |
| TLC (Traffic Light Controller) | The system specified by this document. |
| YELLOW Phase | The traffic signal phase during which the yellow indicator is illuminated, signaling that the signal is transitioning from GREEN to RED and that vehicles should prepare to stop. |
