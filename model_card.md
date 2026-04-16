# BugHound Mini Model Card (Reflection)

---

## 1) What is this system?

**Name:** BugHound
**Purpose:** BugHound is an experimental, agentic Python debugging assistant. Given a code snippet, it analyzes the code for potential issues, proposes a minimal fix, scores the risk of that fix, and decides whether the change is safe enough to apply automatically or should be deferred to a human reviewer.

**Intended users:** Students and early-stage engineers learning how to build, evaluate, and stress-test agentic AI workflows. BugHound is intentionally small and transparent so that its decision-making can be traced, challenged, and improved.

---

## 2) How does it work?

BugHound runs a five-step agentic loop on every submission:

1. **PLAN** — The agent logs its intent: perform a scan and propose a fix. No decisions are made here; it exists to make the workflow observable.

2. **ANALYZE** — The agent detects issues in the code. If a live LLM client (Gemini) is available, it sends the code with a structured prompt and expects a JSON array of `{type, severity, msg}` objects back. If the LLM is unavailable, returns unparseable output, or raises an API error, the agent falls back to a heuristic analyzer that pattern-matches for three specific signals: `print(` calls, bare `except:` blocks, and `TODO` comments.

3. **ACT** — The agent proposes a fix. If issues were found, it follows the same LLM-first, heuristic-fallback pattern. The heuristic fixer replaces bare excepts with `except Exception as e:`, prepends `import logging`, and swaps `print(` calls to `logging.info(`. If no issues were found, the original code is returned unchanged.

4. **TEST** — The proposed fix is passed to `assess_risk()`, a rule-based scoring function that starts at 100 and deducts points for detected issue severity, structural changes (removed return statements, major code shrinkage, mutated string literals), and medium/high severity findings. The result is a score (0–100), a risk level (low/medium/high), a list of reasons, and a `should_autofix` boolean.

5. **REFLECT** — The agent logs its final decision: either "safe to auto-apply" (low risk, no significant issues) or "human review recommended." This step takes no action itself; it records the reasoning.

**Heuristics vs. Gemini:**
- Heuristics are deterministic, offline, and fast, but narrow — they only catch the three patterns they were written for.
- Gemini is richer and can detect issues like unclosed file handles, division-by-zero risk, or missing type annotations, but it is non-deterministic, rate-limited, and can return output that the agent cannot parse, causing silent fallback to heuristics.

---

## 3) Inputs and outputs

**Inputs tested:**

| Snippet | Shape | Description |
|---------|-------|-------------|
| `print_spam.py` | Short function, 4 lines | Two `print()` calls, one `return` |
| `flaky_try_except.py` | Function with try/except, 6 lines | Bare `except:` that swallows errors |
| `mixed_issues.py` | Function with TODO, print, bare except, 9 lines | All three heuristic patterns present |
| `cleanish.py` | Imports + simple function, 5 lines | Uses `logging`, no issues expected |
| Empty string | 0 lines | Edge case: no code at all |
| Comments only | 2 comment lines | `# TODO: do something` — no executable code |
| `print(` in string literal | Function with string containing `print(`, 3 lines | False positive candidate |

**Outputs observed:**

- *Issue types detected:* Code Quality (Low), Reliability (High), Maintainability (Medium)
- *Fixes proposed:* Added `import logging`, replaced `print(` with `logging.info(`, replaced bare `except:` with `except Exception as e:`. Maintainability (TODO) issues were detected but no heuristic fix exists for them — the original code was returned unchanged.
- *Risk reports:* Scores ranged from 30 (HIGH, `mixed_issues.py`) to 95–100 (LOW, `cleanish.py` and `print_spam.py`). Auto-fix was approved only for low-severity, structurally sound fixes with no medium/high issues present.

---

## 4) Reliability and safety rules

**Rule 1: Remove 30 points if `return` statements are absent from the fix**

- *What it checks:* If `return` appears in the original code but not in the proposed fix, the assessor penalizes the fix heavily.
- *Why it matters:* Removing a `return` silently changes a function's behavior — it now returns `None` instead of a value. This is one of the most consequential and hard-to-spot behavioral regressions an automated fixer can introduce.
- *False positive:* A fix that legitimately converts a function to a procedure (e.g. a logging helper that never needed a return value) would be penalized even if the change is intentional.
- *False negative:* If a `return` is present in both versions but its value is changed (e.g. `return True` → `return None`), this rule does not fire.

**Rule 2: Remove 25 points if the fix mutates string literal contents**

- *What it checks:* Extracts all quoted string literals from both the original and fixed code. If any strings that existed in the original are absent from the fix, the score is penalized.
- *Why it matters:* The heuristic fixer uses a simple `str.replace("print(", "logging.info(")` across the entire file. If `print(` appears inside a string literal (e.g. `"use print() to debug"`), the fixer corrupts that string's content — a behavioral change that alters user-visible text or documentation.
- *False positive:* A legitimate refactor that intentionally rewrites a string (e.g. updating an error message) would be incorrectly flagged as risky.
- *False negative:* The regex only catches single-line strings delimited by `"` or `'`. Multi-line strings (triple-quoted) and f-strings with complex expressions are not covered.

---

## 5) Observed failure modes

**Failure 1: False positive on `print(` inside a string literal (over-editing)**

Input:
```python
def docs():
    msg = "use print() to debug"
    return msg
```
The heuristic analyzer uses `if "print(" in code` — a plain substring check. This matched `print(` inside the string literal and flagged a Code Quality issue. The heuristic fixer then replaced `print(` with `logging.info(` across the whole file, mutating the string to `"use logging.info() to debug"`. The original risk assessor scored this 95 (LOW) and marked it safe to auto-apply. The result would have been a silently broken string shipped as an automated fix.

**Failure 2: LLM fallback inconsistency across runs on the same input**

When running `flaky_try_except.py` twice in Gemini mode with the same settings, one run showed `ANALYZE: Using LLM analyzer` (LLM succeeded) while a second run showed `ANALYZE: LLM output was not parseable JSON. Falling back to heuristics.` The final issue list and score were the same in both cases, making the fallback invisible to the user. The agent's behavior was non-deterministic: identical input, identical output, but different internal code paths. This makes it impossible to know whether results were produced by the LLM or by the heuristics without reading the trace log.

---

## 6) Heuristic vs Gemini comparison

| Dimension | Heuristic mode | Gemini mode |
|-----------|---------------|-------------|
| Issues detected | Only `print(`, bare `except:`, `TODO` | Richer: may also flag unclosed file handles, division by zero, missing error context |
| Consistency | Fully deterministic — same input always produces same output | Non-deterministic — output varies across runs; sometimes returns unparseable JSON |
| Fix quality | Mechanical and narrow; cannot fix TODO or logic issues | Context-aware, but may add unrequested changes or produce empty output |
| Risk scoring | Predictable — score is a direct function of the heuristic issues found | Varies — LLM may find more or fewer issues, changing the score significantly |
| API dependency | None — runs fully offline | Requires valid API key; rate-limited to ~20 free requests |
| Fallback visibility | Always uses heuristics; agent trace says "offline mode" | When LLM fails, agent silently uses heuristics — trace is the only signal |

In practice, Gemini and heuristic modes agreed on the same core issues for `flaky_try_except.py` (bare `except:`). For `mixed_issues.py`, Gemini fell back to heuristics mid-run, producing the same three issues the heuristic analyzer would have found. The risk assessor agreed with intuition in both cases: multiple severity levels → HIGH risk → no auto-fix.

---

## 7) Human-in-the-loop decision

**Scenario:** The agent is run on a function that handles file I/O or external API calls. Gemini proposes a fix that restructures the try/except block, changes which exceptions are caught, and adds a new `import`. The risk score comes back at 72 (just below the auto-fix threshold), but the reasons mention a High severity issue and a removed bare except.

**The agent should refuse to auto-fix and surface this to the user because:**
- Any change to exception handling in I/O or network code can silently swallow errors that would otherwise surface as alerts
- The LLM may have changed *which* exceptions are caught, not just *how* they are formatted
- The human writing the code has context about the error-handling contract that the agent cannot infer from the snippet alone

**Where the trigger belongs:** `risk_assessor.py`. A new rule: if the fix modifies any `except` clause AND the original code had a `return` inside that except block, add an additional -20 penalty and append a reason that explicitly requests human review of the exception handling change.

**Message to show the user:**
> "BugHound modified an exception handler that contained a return statement. This may change how errors are surfaced in your application. Please review the diff before applying."

---

## 8) Improvement idea

**Load analyzer and fixer prompts from the `prompts/` files instead of hardcoding them inline.**

Currently, `bughound_agent.py` hardcodes simplified prompts directly in `analyze()` and `propose_fix()`. The `prompts/` folder contains better-structured versions of these prompts — with clearer severity constraints, format rules, and guidance — but they are never loaded. The files are dead code.

**What to change:** At agent initialization, load the four `.txt` files and substitute `{{CODE}}` and `{{ISSUES}}` at call time. This is a one-time file read with a simple `str.replace()`.

**Why it improves reliability:**
- The file prompts enforce the severity enum (`"Low"`, `"Medium"`, `"High"`) more explicitly, reducing the frequency of non-standard values that trigger our normalization fallback
- Separating prompts from code makes them easier to iterate on without touching agent logic
- It reduces the gap between what the system *says* it does (uses prompt files) and what it *actually* does (uses hardcoded strings)

**Complexity:** Low — no new dependencies, no architectural changes, fully backward-compatible.
