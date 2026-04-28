# Software Requirements Specification
# Bench Test Traffic Light Controller

| Field | Value |
|---|---|
| **Document ID** | SRS-TLC-001 |
| **Version** | 1.1 |
| **Date** | 2026-04-28 |
| **Status** | Released |
| **Replaces** | SYS-TLC-001 v1.0 (System Specification, Bench Test Traffic Light Controller) |
| **Prepared by** | sddark |
| **Change Record** | v1.1 — Revised for implementation neutrality; removed color and LED references; renamed states to GO/YIELD/STOP; renamed CRB to PRS; removed SHOULD/MAY modal verbs |

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [Purpose](#11-purpose)
   - 1.2 [Scope](#12-scope)
   - 1.3 [Product Overview](#13-product-overview)
     - 1.3.1 [Product Perspective](#131-product-perspective)
     - 1.3.2 [Product Functions](#132-product-functions)
     - 1.3.3 [User Characteristics](#133-user-characteristics)
     - 1.3.4 [Limitations](#134-limitations)
   - 1.4 [Definitions, Acronyms, and Abbreviations](#14-definitions-acronyms-and-abbreviations)
   - 1.5 [References](#15-references)
   - 1.6 [Overview of Document](#16-overview-of-document)
2. [Overall Description](#2-overall-description)
   - 2.1 [Product Perspective](#21-product-perspective)
   - 2.2 [Product Functions](#22-product-functions)
   - 2.3 [User Characteristics](#23-user-characteristics)
   - 2.4 [Limitations](#24-limitations)
   - 2.5 [Assumptions and Dependencies](#25-assumptions-and-dependencies)
   - 2.6 [Apportioning of Requirements](#26-apportioning-of-requirements)
3. [Requirements](#3-requirements)
   - 3.1 [External Interface Requirements](#31-external-interface-requirements)
     - 3.1.1 [User Interfaces](#311-user-interfaces)
     - 3.1.2 [Hardware Interfaces](#312-hardware-interfaces)
     - 3.1.3 [Software Interfaces](#313-software-interfaces)
     - 3.1.4 [Communications Interfaces](#314-communications-interfaces)
   - 3.2 [Functions](#32-functions)
   - 3.3 [Usability Requirements](#33-usability-requirements)
   - 3.4 [Performance Requirements](#34-performance-requirements)
   - 3.5 [Logical Database Requirements](#35-logical-database-requirements)
   - 3.6 [Design Constraints](#36-design-constraints)
   - 3.7 [Software System Attributes](#37-software-system-attributes)
     - 3.7.1 [Reliability](#371-reliability)
     - 3.7.2 [Availability](#372-availability)
     - 3.7.3 [Maintainability](#373-maintainability)
     - 3.7.4 [Portability](#374-portability)
   - 3.8 [Supporting Information](#38-supporting-information)
4. [Verification](#4-verification)
5. [Appendices](#5-appendices)
   - Appendix A: [Behavioral Specification](#appendix-a-behavioral-specification)
   - Appendix B: [Open Questions](#appendix-b-open-questions)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete set of functional and non-functional requirements for the Bench Test Traffic Light Controller (TLC). It establishes what the system must do and the measurable quality thresholds the system must meet.

This document is intended to be an example of an SRS document using a bench test TLC as a subject.

### 1.2 Scope

The system specified by this document is named the **Bench Test Traffic Light Controller (TLC)**.

The TLC simulates a single-lane, single-intersection traffic signal with an integrated pedestrian crosswalk request capability. It is intended for demonstration purposes.

The TLC's objective:

- Cycle through traffic signal phases in a defined order and with defined timing
- Accept a pedestrian crosswalk request via a single input signal
- Insert a pedestrian walk interval at the appropriate point in the signal cycle
- Produce all observable output exclusively through three discrete indicators

### 1.3 Product Overview

#### 1.3.1 Product Perspective

The TLC is a self-contained, standalone bench prototype. It does not form part of a larger system and has no external network, data, or control dependencies. All inputs arrive through a single Pedestrian Request Signal (PRS); all outputs are produced by three discrete indicators. The system receives power from a single external supply and requires no operator interaction during normal operation beyond the optional pedestrian request.

The context of use is a lab bench.

#### 1.3.2 Product Functions

The TLC provides the following principal functions:

1. **Continuous traffic signal cycling** — The system cycles the indicators through GO, YIELD, and STOP phases in a fixed order with defined durations, repeating indefinitely.
2. **Pedestrian crosswalk request handling** — The system accepts a Pedestrian Request Signal (PRS) from a simulated pedestrian, latches the request, and inserts a PEDESTRIAN phase at the earliest safe opportunity following the current STOP phase.
3. **Input validation** — The system filters spurious or transient PRS signals so that a single physical activation registers as exactly one logical request event.
4. **Defined startup behavior** — Upon power application, the system enters the GO phase within a bounded time and begins normal cycling.
5. **Undefined-state protection** — If the system enters an unrecognized state, it defaults to a safe, stationary condition with only the STOP indicator active.

#### 1.3.3 User Characteristics

Roles which interact with this system:

| Role | Description | Expected Interaction |
|---|---|---|
| Lab Operator | An engineer or student assembling and verifying the prototype | Powers the system on and off; observes indicator states; validates timing against this specification

#### 1.3.4 Limitations

The following limitations apply to this prototype and constrain what the system is required to do:

1. The system controls exactly three indicators and accepts exactly one input signal. No additional I/O channels are defined.
2. The system is a single-intersection prototype. No multi-intersection coordination is defined or implied.
3. The PEDESTRIAN phase shares the STOP indicator. A dedicated pedestrian WALK / DON'T WALK indicator is outside the scope of this prototype.
4. Timing values are fixed at design time and are not configurable by an operator at runtime.
5. The system does not provide any acknowledgment output to notify the pedestrian that a crosswalk request has been registered.
6. No audible signals, accessibility outputs, or emergency preemption are provided.
7. No fault detection, diagnostics, or self-test modes are defined.

### 1.4 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| Active Indicator | The single indicator that is in the active state during a given phase. |
| Bench Prototype | A hardware assembly constructed on a breadboard or development surface, intended for demonstration and verification rather than production deployment. |
| CR | Crosswalk Request — a latched internal flag indicating that a pedestrian has made a valid request for a walk interval. |
| GO Indicator | The indicator that is active during the GO phase, signaling that vehicle traffic has right of way. |
| GO Phase | The traffic signal phase during which the GO indicator is active and vehicle traffic has right of way. |
| IEEE | Institute of Electrical and Electronics Engineers. |
| Indicator | A discrete visual output used to communicate signal state to observers. The physical form of the indicator is an implementation decision. |
| Latched | A state that is retained in memory until explicitly cleared by a defined system event. |
| Nominal | The intended or target value of a parameter under standard operating conditions. |
| PEDESTRIAN Phase | The traffic signal phase during which pedestrians have right of way to cross. Vehicle traffic is stopped during this phase. The STOP indicator is active during this phase. |
| Phase | A discrete, timed operating mode of the traffic light controller, associated with a specific indicator state and a defined duration. |
| Phase Duration | The length of time the system remains in a given phase before evaluating transition conditions. |
| Phase Transition Latency | The elapsed time between the scheduled end of one phase and the activation of the first indicator of the next phase. |
| Post-Activation Lockout | A time window following a valid PRS activation during which additional PRS signals are ignored. |
| PRS | Pedestrian Request Signal — the single input through which a pedestrian signals a crosswalk request. |
| SHALL | Used to indicate a mandatory requirement, per RFC 2119 convention. |
| SRS | Software Requirements Specification. |
| Stability Timer | An internal timing measurement confirming that a PRS signal has held a given state for a minimum duration before the transition is accepted as valid. |
| State Machine | A behavioral model in which the system is always in exactly one of a finite set of defined states, with transitions governed by explicit conditions. |
| STOP Indicator | The indicator that is active during the STOP phase and PEDESTRIAN phase, signaling that vehicle traffic must stop. |
| STOP Phase | The traffic signal phase during which the STOP indicator is active and vehicle traffic must stop. |
| TLC | Traffic Light Controller — the system specified by this document. |
| YIELD Indicator | The indicator that is active during the YIELD phase, signaling that the signal is transitioning from GO to STOP. |
| YIELD Phase | The traffic signal phase during which the YIELD indicator is active, signaling that the signal is transitioning from GO to STOP. |

### 1.5 References

| Reference ID | Document Title | Version | Date |
|---|---|---|---|
| SYS-TLC-001 | Bench Test Traffic Light Controller — System Specification | 1.0 | 2026-04-26 |
| IEEE 29148-2018 | Systems and Software Engineering — Life Cycle Processes — Requirements Engineering | 2018 | 2018 |


### 1.6 Overview of Document

**Section 1 (Introduction)** establishes the purpose, scope, and context of this document and defines the terminology used throughout.

**Section 2 (Overall Description)** describes the system's context, summarizes its functions, characterizes its users, and documents assumptions and dependencies that affect the requirements.

**Section 3 (Requirements)** specifies all functional requirements (FR-001 through FR-020), non-functional requirements (NF-001 through NF-010), and design constraints (C-001 through C-005), organized per IEEE 29148-2018 subsection structure.

**Section 4 (Verification)** provides a traceability table mapping every requirement to its verification method and associated test reference.

**Appendix A (Behavioral Specification)** provides the formal state machine definition, input validation flow, edge case scenarios, and timing diagrams that elaborate on the requirements in Section 3.

**Appendix B (Open Questions)** records unresolved questions from the predecessor system specification, noting which have been resolved by the architecture.

---

## 2. Overall Description

### 2.1 Product Perspective

The TLC operates as an independent system with no upstream or downstream system connections. Its boundary is defined by:

- **One physical input:** the Pedestrian Request Signal (PRS)
- **Three physical outputs:** discrete GO, YIELD, and STOP indicators
- **One power input:** a single external supply

All system behavior is internally governed. No external clock, network signal, or configuration input is defined.

### 2.2 Product Functions

The TLC provides five functions. Each is elaborated in the requirements of Section 3.2.

| Function | Summary |
|---|---|
| F-1: Normal Traffic Signal Cycling | Continuously cycle the indicators GO → YIELD → STOP → GO with defined durations and mutual exclusion |
| F-2: Pedestrian Crosswalk Request | Accept, latch, and service a PRS activation by inserting a PEDESTRIAN phase at the conclusion of the current STOP phase |
| F-4: Defined Startup | Enter the GO phase within 500 ms of power application with all indicators inactive beforehand |
| F-5: Undefined-State Protection | Halt phase progression and activate only the STOP indicator if the system enters an unrecognized state |

### 2.3 User Characteristics

See Section 1.3.3. No additional characteristics apply.

### 2.4 Limitations

See Section 1.3.4. All limitations stated there apply throughout this document.

### 2.5 Assumptions and Dependencies

**A-001** — The power supply to the system is stable during normal operation. Voltage sags or noise on the supply line that cause behavioral anomalies are outside the scope of this specification.

**A-002** — The PRS produces a two-state signal. The system assumes signal transients are confined to the first 20 milliseconds following a state transition. The 50 ms qualification window in FR-019 provides margin above this assumption.

**A-003** — The lab environment provides consistent ambient conditions such that indicator states are visually unambiguous at a 2-meter observation distance.

**A-004** — The system operates continuously once powered. There is no sleep, standby, or low-power mode.

**A-005** — Only one pedestrian activates the PRS at a time. Simultaneous multi-person activation is not a considered scenario for this prototype.

### 2.6 Apportioning of Requirements

All requirements in this SRS are allocated to a single system: the TLC. This is a standalone prototype; no requirements are delegated to external systems, subsystems, or external services.

---

## 3. Requirements

### 3.1 External Interface Requirements

#### 3.1.1 User Interfaces

The TLC provides no graphical, textual, or display-based user interface. All interaction occurs through the physical hardware interfaces defined in Section 3.1.2.

The Lab Operator interacts with the system by:

- Applying and removing power via the external power supply connection
- Observing the three indicator outputs to verify system behavior

The Simulated Pedestrian interacts with the system by:

- Activating the Pedestrian Request Signal (PRS)

No configuration, menu, or command input interface exists.

#### 3.1.2 Hardware Interfaces

##### Pedestrian Request Signal (PRS) — Input

| Property | Specification |
|---|---|
| Type | Momentary contact, normally open |
| Signal type | Digital input, active-low (activated = low signal level, released = high signal level) |
| Pull configuration | Signal held to high state via pull resistor when open; activation drives the signal to low state |
| Minimum activation duration for detection | 50 milliseconds (per FR-019) |
| Post-activation lockout | 300 milliseconds minimum (per FR-020) |
| Expected contact bounce duration | Up to 20 milliseconds; the system shall tolerate this (per A-002) |

##### STOP Indicator — Output

| Property | Specification |
|---|---|
| Signal type | Digital output, two-state (active / inactive) |
| Active during phases | STOP, PEDESTRIAN |
| Inactive during phases | GO, YIELD |
| Activation/deactivation transition time | Less than 5 milliseconds (imperceptible to human observer) |

##### YIELD Indicator — Output

| Property | Specification |
|---|---|
| Signal type | Digital output, two-state (active / inactive) |
| Active during phases | YIELD |
| Inactive during phases | GO, STOP, PEDESTRIAN |
| Activation/deactivation transition time | Less than 5 milliseconds (imperceptible to human observer) |

##### GO Indicator — Output

| Property | Specification |
|---|---|
| Signal type | Digital output, two-state (active / inactive) |
| Active during phases | GO |
| Inactive during phases | YIELD, STOP, PEDESTRIAN |
| Activation/deactivation transition time | Less than 5 milliseconds (imperceptible to human observer) |

##### Power Interface

| Property | Specification |
|---|---|
| Power source | Single external supply consistent with the development platform in use |
| Startup behavior | System enters GO phase within 500 ms of power application (FR-017) |
| Power loss behavior | All indicators become inactive immediately upon power loss; system resets to GO phase on restoration (NF-007) |

#### 3.1.3 Software Interfaces

No external software interfaces are defined. The TLC does not communicate with any external software system, operating system service (beyond those required by the hosting platform), or network endpoint.

#### 3.1.4 Communications Interfaces

No communications interfaces are defined. The TLC has no network, serial, or wireless communication capability.

---

### 3.2 Functions

Requirements are grouped by the function they satisfy. All requirement identifiers are stable and match those in SYS-TLC-001.

---

#### F-1: Normal Traffic Signal Cycling

**FR-001** — The system SHALL continuously cycle through the following phases in the following order when no Crosswalk Request is pending:

> GO → YIELD → STOP → GO → (repeat)

**FR-002** — During the GO phase, only the GO indicator SHALL be active; the STOP and YIELD indicators SHALL be inactive.

**FR-003** — During the YIELD phase, only the YIELD indicator SHALL be active; the STOP and GO indicators SHALL be inactive.

**FR-004** — During the STOP phase, only the STOP indicator SHALL be active; the GO and YIELD indicators SHALL be inactive.

**FR-005** — The system SHALL have exactly one indicator active at a time during normal cycling. No two indicators SHALL be simultaneously active, and no indicator SHALL be inactive when the system is in a steady state (non-transitioning).

*Rationale: FR-005 is a safety-clarity invariant for the demonstration. It makes the current phase unambiguous to observers at all times and prevents undefined mixed states.*

---

#### F-2: Pedestrian Crosswalk Request

**FR-006** — The system SHALL monitor the Pedestrian Request Signal (PRS) at all times, including during phase transitions.

**FR-007** — A single valid PRS activation SHALL register a Crosswalk Request. The system SHALL latch this request in a pending state until it is serviced or invalidated per FR-012.

**FR-008** — The system SHALL service a pending Crosswalk Request by inserting a PEDESTRIAN phase between the STOP phase and the subsequent GO phase.

**FR-009** — During the PEDESTRIAN phase, only the STOP indicator SHALL be active. The GO and YIELD indicators SHALL be inactive.

*Rationale: FR-009 follows from C-003. The STOP indicator is shared between the STOP phase and the PEDESTRIAN phase in this prototype because a dedicated pedestrian indicator is out of scope.*

**FR-010** — When the system transitions from the STOP phase to the PEDESTRIAN phase, the system SHALL clear the pending Crosswalk Request. After the PEDESTRIAN phase completes, the system SHALL resume the normal cycle, beginning with the GO phase.

**FR-011** — If the PRS is activated while the system is in the STOP phase and no PEDESTRIAN phase has yet begun for that STOP interval, the system SHALL insert a PEDESTRIAN phase at the conclusion of the current STOP phase duration. The STOP phase SHALL complete its full minimum duration before the PEDESTRIAN phase begins.

**FR-012** — If the PRS is activated while the system is in the PEDESTRIAN phase, the activation SHALL be ignored. The system SHALL NOT extend the PEDESTRIAN phase duration and SHALL NOT latch an additional pending request.

**FR-013** — If the PRS is activated multiple times before the Crosswalk Request is serviced, the system SHALL treat all subsequent activations as redundant. Only one PEDESTRIAN phase SHALL be inserted per service cycle.

**FR-014** — If the PRS is activated during the GO phase, the system SHALL latch a pending Crosswalk Request and SHALL service it at the end of the next STOP phase (i.e., after the system completes GO → YIELD → STOP in full, then inserts PEDESTRIAN).

**FR-015** — If the PRS is activated during the YIELD phase, the system SHALL latch a pending Crosswalk Request (if not already latched) and SHALL service it at the end of the subsequent STOP phase.

---

#### F-4: Defined Startup

**FR-016** — Upon power-on, the system SHALL enter the GO phase and begin normal cycling from that point.

**FR-017** — All indicators SHALL be inactive for no more than 500 milliseconds from the moment power is applied before the GO phase indicator becomes active.

*Rationale: FR-017 sets an upper bound on the inactive period at startup so that an observer cannot miss the transition into the first active phase.*

---

#### F-5: Undefined-State Protection

*(Expressed as design constraint C-004 in Section 3.6 below, per the structural convention of this SRS. The constraint is stated there with full behavioral specification.)*

---

### 3.3 Usability Requirements

**U-001** — The system SHALL require no operator interaction during normal cycling. Once powered on, the system SHALL cycle without intervention indefinitely.

**U-002** — The Pedestrian Request Signal SHALL require no more than a single momentary activation to register a Crosswalk Request. No multi-step activation sequence is required.

**U-003** — All indicator state transitions SHALL be observable without specialized equipment by a Lab Operator seated within 2 meters of the bench assembly under standard indoor lighting conditions (see NF-009).

### 3.4 Performance Requirements

**NF-005** — Phase transition latency — the elapsed time between the scheduled end of one phase and the activation of the first indicator of the next phase — SHALL NOT exceed 50 milliseconds.

### 3.5 Logical Database Requirements

The TLC maintains runtime state. No persistent storage (across power cycles) is required or permitted. The following entities describe the logical data model.

#### System State Record

Represents the complete runtime state of the controller at any point in time.

| Attribute | Description | Possible Values |
|---|---|---|
| Current Phase | The active phase the system is executing | GO, YIELD, STOP, PEDESTRIAN |
| Phase Elapsed Time | Time elapsed since the current phase began | 0 ms to phase maximum duration |
| Crosswalk Request Pending | Whether a CR has been registered and not yet serviced | True, False |
| PRS Request Suppression Active | Whether the system is currently suppressing PRS activations per FR-020 | True, False |

#### Crosswalk Request Event

Represents a single validated PRS activation.

| Attribute | Description |
|---|---|
| Registration Timestamp | The time at which the PRS activation was validated and recorded |
| Serviced | Whether this request has been consumed by a PEDESTRIAN phase |

#### Relationships

- The System State Record contains exactly one Current Phase at all times.
- At most one Crosswalk Request Event SHALL be pending at any given time.
- A Crosswalk Request Event is created upon a valid PRS activation and is consumed (destroyed) when the PEDESTRIAN phase it triggered concludes.
- All runtime state SHALL be initialized to known values on each power-on. No state carries over across power interruptions.

### 3.6 Design Constraints

**C-001** — The system is a single-intersection prototype. No multi-intersection coordination behavior is defined or implied by any requirement in this specification.

**C-002** — The system has exactly three indicator outputs and exactly one input signal. No additional I/O channels are defined.

**C-003** — The PEDESTRIAN phase shares the STOP indicator. A separate dedicated pedestrian indicator is out of scope for this prototype (see Section 1.3.4).

**C-004** — The system SHALL NOT remain in any undefined state. If an unspecified condition arises, the system SHALL immediately activate only the STOP indicator, deactivate the YIELD and GO indicators, and halt phase progression. The system SHALL remain in this safe halt condition until power is cycled. Normal operation SHALL resume from the GO phase upon power restoration per FR-016.

*Rationale: C-004 provides a deterministic fail-safe for any implementation fault that results in an unrecognized system state. Activating only the STOP indicator is the safest observable condition for vehicle and pedestrian actors.*

**C-005** — Timing values specified in Section 3.4 are fixed for this prototype and are not operator-configurable at runtime.

### 3.7 Software System Attributes

#### 3.7.1 Reliability

**NF-010** — The system SHALL produce no ambiguous indicator states (e.g., partial activation, flickering) outside of the defined phase transition window of 50 milliseconds.

*Rationale: Any state in which two indicators appear simultaneously active, or in which an indicator fluctuates irregularly, constitutes an undefined signal state that cannot be correctly interpreted by simulated drivers or pedestrians.*

The system SHALL exhibit deterministic behavior on every power cycle: the same startup sequence, the same initial phase, and the same transition rules SHALL apply on every power-on regardless of how many times the system has been cycled or what state it was in when power was removed.

#### 3.7.2 Availability

**NF-007** — The system SHALL resume normal cycling without operator intervention after any single power interruption and restoration. Upon restoration, the system SHALL enter the GO phase per FR-016. Any pending Crosswalk Request that existed before the interruption SHALL be considered lost; no PEDESTRIAN phase SHALL be automatically inserted on the first cycle following restoration.

**NF-008** — The system SHALL operate continuously without degradation in timing accuracy for a minimum of 8 hours of uninterrupted operation. YIELD phase measurements taken at any point during the 8-hour period SHALL remain within the ±100 millisecond tolerance specified in NF-002.

#### 3.7.3 Maintainability

The timing values for each phase (GO, YIELD, STOP, PEDESTRIAN durations) and the input validation parameters (qualification window and request suppression period per FR-019 and FR-020) SHALL each be defined in one location within the implementation. Changing any one timing value SHALL require modification in exactly one location and SHALL NOT require changes elsewhere in the implementation.

*Rationale: This constraint ensures that future adjustments to phase durations or input validation timing can be made without risk of introducing inconsistencies across the implementation.*

#### 3.7.4 Portability

All behavioral requirements in this SRS SHALL be satisfiable by any implementation that can:

- Control three discrete digital output signals
- Read one discrete digital input signal
- Measure elapsed time with a resolution of at least 10 milliseconds
- Execute a control loop at a rate of at least 20 Hz (one iteration every 50 milliseconds)

No requirement in this SRS mandates a specific development platform, operating system, programming language, library, or hardware component. Hardware interface signal types are specified in Section 3.1.2 at the logical level only.

### 3.8 Supporting Information

The formal behavioral specification supporting the requirements in Section 3.2 — including the state machine transition table, input validation scenarios, edge case scenarios, and timing diagrams — is provided in Appendix A.

Open questions from the predecessor system specification and their resolution status are documented in Appendix B.

---

## 5. Appendices

### Appendix A: Behavioral Specification

This appendix provides the formal behavioral elaborations that support the functional requirements in Section 3.2. These descriptions define expected observable behavior and may be used to derive detailed test procedures.

#### A.1 State Machine Definition

The system operates as a deterministic finite state machine with four operational states and one fault state.

##### State Definitions

| State ID | Name | Description | Active Indicator |
|---|---|---|---|
| S1 | GO | Vehicle traffic has right of way | GO indicator |
| S2 | YIELD | Traffic signal is transitioning; vehicle traffic shall prepare to stop | YIELD indicator |
| S3 | STOP | Vehicle traffic must stop | STOP indicator |
| S4 | PEDESTRIAN | Pedestrians have right of way to cross | STOP indicator |
| SF | FAULT | Undefined state detected; safe halt active | STOP indicator |

##### State Transition Table

| Current State | Condition | Next State | Notes |
|---|---|---|---|
| S1 — GO | Phase duration elapsed AND no CR pending | S2 — YIELD | Normal progression |
| S1 — GO | Phase duration elapsed AND CR pending | S2 — YIELD | CR carried forward unchanged |
| S2 — YIELD | Phase duration elapsed AND no CR pending | S3 — STOP | Normal progression |
| S2 — YIELD | Phase duration elapsed AND CR pending | S3 — STOP | CR carried forward unchanged |
| S3 — STOP | Phase duration elapsed AND no CR pending | S1 — GO | Normal progression |
| S3 — STOP | Phase duration elapsed AND CR pending | S4 — PEDESTRIAN | CR cleared upon this transition |
| S4 — PEDESTRIAN | Phase duration elapsed | S1 — GO | CR already cleared; normal cycle resumes |
| Any state | Unrecognized state value detected | SF — FAULT | C-004; STOP indicator only; halt until power cycle |

Note: A CR registered during S1 or S2 is carried forward through those states unchanged. It is evaluated and consumed only at the conclusion of S3. SF has no exit transition; power cycling is the only recovery.

##### Indicator Output by State

| State | STOP Indicator | YIELD Indicator | GO Indicator |
|---|---|---|---|
| S1 — GO | inactive | inactive | active |
| S2 — YIELD | inactive | active | inactive |
| S3 — STOP | active | inactive | inactive |
| S4 — PEDESTRIAN | active | inactive | inactive |
| SF — FAULT | active | inactive | inactive |

##### Crosswalk Request (CR) Latch Rules

| Current State | valid_activation_event | CR Pending | Action |
|---|---|---|---|
| S4 (PEDESTRIAN) | True | Any | Discard activation; no latch (FR-012) |
| S1, S2, or S3 | True | False | Set CR pending (FR-007, FR-014, FR-015) |
| S1, S2, or S3 | True | True | Discard activation; already latched (FR-013) |
| Any | False | Any | No action |

#### A.2 Pedestrian Request Signal Validation Flow

The following scenarios describe the processing of a single physical PRS activation. The validation process comprises a qualification window (50 ms per FR-019) and a subsequent request suppression period (300 ms per FR-020).

**Scenario A.2.1 — Valid Activation Registration**

Given the PRS is in the released state and no suppression period is active,
When the PRS transitions to the activated state,
Then the system SHALL begin a qualification timer of 50 milliseconds.

Given the qualification timer is running,
When the PRS remains continuously in the activated state for 50 milliseconds,
Then the system SHALL register one valid activation event and apply the request suppression period for 300 milliseconds.

**Scenario A.2.2 — Transient Signal Rejection**

Given the qualification timer is running,
When the PRS returns to the released state before 50 milliseconds have elapsed,
Then the system SHALL cancel the qualification timer and SHALL NOT register an activation event.

**Scenario A.2.3 — Request Suppression**

Given the request suppression period is active,
When any transition is detected on the PRS,
Then the system SHALL ignore that transition and SHALL NOT start a new qualification timer.

**Scenario A.2.4 — Suppression Period Expiry**

Given the request suppression period is active,
When 300 milliseconds have elapsed since the suppression period was applied,
Then the system SHALL deactivate the suppression period and resume normal PRS monitoring.

#### A.3 Edge Case Scenarios

##### Edge Case A — PRS Activation During YIELD Phase (FR-015)

Given the system is in S2 (YIELD) and no CR is pending,
When a valid PRS activation is registered,
Then the system SHALL latch a pending CR.
And the YIELD phase SHALL continue for its full duration without interruption.
And the system SHALL transition to S3 (STOP) upon YIELD phase completion.
And the system SHALL transition to S4 (PEDESTRIAN) upon STOP phase completion.

##### Edge Case B — PRS Activation During PEDESTRIAN Phase (FR-012)

Given the system is in S4 (PEDESTRIAN),
When a valid PRS activation is registered,
Then the system SHALL ignore the activation entirely.
And the PEDESTRIAN phase SHALL continue for its full duration.
And no new CR SHALL be latched.
And the subsequent cycle SHALL proceed as GO → YIELD → STOP without a PEDESTRIAN phase insertion.

##### Edge Case C — PRS Activated Multiple Times Before Service (FR-013)

Given a CR is already pending,
When one or more additional valid PRS activations are registered before the CR is serviced,
Then each additional activation SHALL be discarded.
And exactly one PEDESTRIAN phase SHALL be inserted when the pending CR is serviced.

##### Edge Case D — PRS Activation at the Instant STOP Phase Begins (FR-011)

Given the system has just entered S3 (STOP) within the same control cycle,
When a valid PRS activation is registered during S3,
Then the system SHALL latch a pending CR.
And the STOP phase SHALL complete its full minimum duration before transitioning.
And the system SHALL then transition to S4 (PEDESTRIAN).

##### Edge Case E — PRS Activation During GO Phase (FR-014)

Given the system is in S1 (GO) and no CR is pending,
When a valid PRS activation is registered,
Then the system SHALL latch a pending CR.
And the GO phase SHALL continue for its remaining scheduled duration without alteration.
And the system SHALL transition through S2 (YIELD) and S3 (STOP) normally.
And the system SHALL insert S4 (PEDESTRIAN) after S3 completes.

##### Edge Case F — Power Interruption with Pending CR (NF-007)

Given a CR is pending and the system is in any state,
When power is interrupted and subsequently restored,
Then the system SHALL restart in S1 (GO) with no pending CR.
And the prior crosswalk request SHALL be considered lost; no PEDESTRIAN phase SHALL be automatically inserted.

#### A.4 Timing Diagrams

##### A.4.1 Nominal Cycle — No Crosswalk Request

```
Time (seconds):    0    7   10   17   20
                   |    |    |    |    |
GO                 [==========]
YIELD                          [====]
STOP                                 [=========]
GO                                              [=======...
```

Phases: GO (7 s nominal) → YIELD (3 s) → STOP (7 s nominal) → repeat.

##### A.4.2 Nominal Cycle — Crosswalk Request During GO

```
Time (seconds):    0    7   10   17   27   37
                   |    |    |    |    |    |
GO                 [==========]
PRS Activation        []
YIELD                          [====]
STOP                                 [=========]
PEDESTRIAN                                      [=======]
```

CR registered during GO is carried through YIELD and STOP. PEDESTRIAN phase (10 s) follows STOP completion. Normal cycle resumes from GO after PEDESTRIAN phase.

---

### Appendix B: Open Questions

The following open questions were identified in SYS-TLC-001 v1.0. Their status as of the architecture document ARCH-TLC-001 v1.0 is noted.

---

**OQ-001** — Should the PEDESTRIAN phase provide any visual countdown indication (e.g., a pulsing STOP indicator in the final seconds)?

This specification currently defines a static STOP indicator for the full PEDESTRIAN phase duration.

**Resolution (ARCH-TLC-001):** Resolved — closed. The architecture implements a static STOP indicator for the full PEDESTRIAN phase duration. No pulsing pattern is defined or implemented. SYS-TLC-001 Section 3.2 explicitly places a dedicated pedestrian indicator out of scope. If a blink requirement is added in a future revision of this SRS, this open question shall be reopened.

---

**OQ-002** — Should the system support an operator-accessible reset mechanism (e.g., a second input that restarts the cycle to GO) without requiring a full power cycle?

Currently, no such mechanism is defined.

**Resolution (ARCH-TLC-001):** Resolved — closed. No hardware reset input is implemented. The power-cycling behavior defined by FR-016, FR-017, and NF-007 serves as the reset mechanism for this prototype. Adding a reset input without a specification change would introduce unspecified state-machine behavior (e.g., what happens to a pending CR during reset). Stakeholder direction is required to reopen this question.

---

**OQ-003** — Should a CR registered during the PEDESTRIAN phase be latched for the next cycle rather than discarded (per FR-012)?

The current specification discards it for simplicity.

**Resolution (ARCH-TLC-001):** Resolved — closed. The architecture enforces the FR-012 discard behavior. Queuing a CR during PEDESTRIAN would require multi-request tracking, which contradicts the single-pending-request model of FR-013. If queueing behavior is desired, FR-012 and FR-013 must be revised in a future SRS version before implementation changes are made.

---

**OQ-004** — Are the nominal phase durations (7 s GO, 3 s YIELD, 7 s STOP, 10 s PEDESTRIAN) acceptable for the intended demonstration, or should they be adjusted to better fit the lab session duration?

**Resolution (ARCH-TLC-001):** Resolved — closed for the current version. All durations are implemented at their nominal values as specified in NF-001 through NF-004. Per the maintainability requirement in Section 3.7.3, adjusting any duration requires modifying exactly one location in the implementation. This question should be revisited if user feedback indicates the demonstration timing is unsuitable.

---

**OQ-005** — Should the system provide any output (e.g., a dedicated indicator) to signal to the pedestrian that their request has been registered and is pending?

Currently, no acknowledgment output is defined.

**Resolution (ARCH-TLC-001):** Resolved — closed. No dedicated acknowledgment indicator is implemented. The Crosswalk Request is an internal state only. Constraint C-002 limits the system to exactly three indicator outputs and one input signal. Adding an acknowledgment indicator requires a revision to C-002 and stakeholder approval before this question is reopened.

---

*End of SRS-TLC-001 v1.1*
