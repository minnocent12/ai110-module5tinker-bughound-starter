# 🐶 BugHound

BugHound is a small, agent-style debugging tool. It analyzes a Python code snippet, proposes a fix, and runs basic reliability checks before deciding whether the fix is safe to apply automatically.

---

## What BugHound Does

Given a short Python snippet, BugHound:

1. **Analyzes** the code for potential issues  
   - Uses heuristics in offline mode  
   - Uses Gemini when API access is enabled  

2. **Proposes a fix**  
   - Either heuristic-based or LLM-generated  
   - Attempts minimal, behavior-preserving changes  

3. **Assesses risk**  
   - Scores the fix  
   - Flags high-risk changes  
   - Decides whether the fix should be auto-applied or reviewed by a human  

4. **Shows its work**  
   - Displays detected issues  
   - Shows a diff between original and fixed code  
   - Logs each agent step

---

## Setup

### 1. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running in Offline (Heuristic) Mode

No API key required.

```bash
streamlit run bughound_app.py
```

In the sidebar, select:

* **Model mode:** Heuristic only (no API)

This mode uses simple pattern-based rules and is useful for testing the workflow without network access.

---

## Running with Gemini

### 1. Set up your API key

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```text
GEMINI_API_KEY=your_real_key_here
```

### 2. Run the app

```bash
streamlit run bughound_app.py
```

In the sidebar, select:

* **Model mode:** Gemini (requires API key)
* Choose a Gemini model and temperature

BugHound will now use Gemini for analysis and fix generation, while still applying local reliability checks.

---

## Running Tests

Tests focus on **reliability logic** and **agent behavior**, not the UI.

```bash
PYTHONPATH=. pytest tests/ -v
```

> Note: `PYTHONPATH=.` is required so pytest can resolve `bughound_agent` and `reliability` as top-level modules.

The 9 tests cover:

* Risk scoring and guardrails (`test_risk_assessor.py`)
* Heuristic fallbacks when LLM output is invalid (`test_agent_workflow.py`)
* End-to-end agent workflow shape and output types
* String literal mutation detection — prevents false-positive heuristics from auto-applying over-edits
* Medium/High severity issue gate — blocks auto-fix even when the risk score is technically low

---

## Reliability Guardrails

Three guardrails were added beyond the starter implementation:

| Guardrail | Location | What it prevents |
|-----------|----------|-----------------|
| Severity normalization | `bughound_agent._normalize_issues` | Non-standard severity values (e.g. `"Critical"`, `"MEDIUM"`) silently bypassing risk scoring |
| Medium/High severity gate | `risk_assessor.assess_risk` | Auto-fix triggering on notable issues even when the score is ≥ 75 |
| String literal mutation | `risk_assessor.assess_risk` | Heuristic false positives rewriting text inside string literals and auto-applying the change |

---

## Demo

### Test 1 — Clean Code (No Issues)
![Clean code](demo/01_clean_code.png)

### Test 2 — Bare Except (High Severity)
![Bare except](demo/02_bare_except.png)

### Test 3 — All Three Heuristic Patterns
![Mixed issues](demo/03_mixed_issues.png)

### Test 4 — Medium Severity Blocks Auto-Fix (Part 3 Guardrail)
![Medium severity guardrail](demo/04_medium_severity_guardrail.png)

### Test 5 — String Literal Mutation Blocked (Part 4 Guardrail)
![String literal guardrail](demo/05_string_literal_guardrail.png)

### Test 6 — Edge Case: Comments Only
![Comments only](demo/06_edge_case_comments_only.png)

### Test 7 — Gemini Mode Sidebar Warning
![Gemini mode warning](demo/07_gemini_mode_warning.png)
