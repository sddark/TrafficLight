---
name: TLC documentation formatting conventions
description: Formatting and style conventions established for TLC wiki documents
type: project
---

Markdown flavor is GitHub-flavored Markdown (GFM). No emojis.

Document header pattern: title (H1), then a small metadata block with document reference, audience, and purpose on consecutive bold-label lines.

Tables are used extensively: wiring tables, phase timing tables, module summary tables, decision rationale tables. Tables are preferred over prose lists for structured data.

Requirement IDs (FR-001, NF-001, C-004, etc.) always appear in backtick inline code when referenced in prose (e.g., `FR-005`). They appear as plain text in table cells.

Code blocks always carry a language label (`bash`, `python`).

The canonical run command is:
```bash
cd ~/Desktop/TrafficLight/Agentic
python3 -m tlc.main
```
The project root for the user is `~/Desktop/TrafficLight/Agentic` (Windows path: `C:\Users\Half-Life\Desktop\Claude\Sys_vs_SW\TrafficLight\Agentic`).

**How to apply:** Follow these conventions for any new TLC documentation pages to maintain consistency with existing docs.
