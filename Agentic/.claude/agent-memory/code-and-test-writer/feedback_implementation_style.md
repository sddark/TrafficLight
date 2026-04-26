---
name: Implementation style for this project
description: User provides fully-specified implementation code; write it exactly as given, then diagnose failures by reading test files carefully rather than guessing
type: feedback
---

The user supplies complete, annotated implementation code in the task prompt. Write the files exactly as given (no creative interpretation), then run the tests and fix the implementation to match what the tests actually assert.

**Why:** The supplied code may contain subtle semantic ambiguities (e.g., "cleared after walk" vs "cleared on entry to walk"). The tests are the authoritative spec; read each failing test's assertions and comments before editing anything.

**How to apply:** When tests fail, read the specific failing test's setup helper and every `assert` line carefully. The fix is almost always a one-line change in the SM or debounce logic, not a structural rewrite. Never modify test files.
