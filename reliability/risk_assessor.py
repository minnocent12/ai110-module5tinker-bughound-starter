import re
from typing import Dict, List


def assess_risk(
    original_code: str,
    fixed_code: str,
    issues: List[Dict[str, str]],
) -> Dict[str, object]:
    """
    Simple, explicit risk assessment used as a guardrail layer.

    Returns a dict with:
    - score: int from 0 to 100
    - level: "low" | "medium" | "high"
    - reasons: list of strings explaining deductions
    - should_autofix: bool
    """

    reasons: List[str] = []
    score = 100

    if not fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["No fix was produced."],
            "should_autofix": False,
        }

    original_lines = original_code.strip().splitlines()
    fixed_lines = fixed_code.strip().splitlines()

    # ----------------------------
    # Issue severity based risk
    # ----------------------------
    for issue in issues:
        severity = str(issue.get("severity", "")).lower()

        if severity == "high":
            score -= 40
            reasons.append("High severity issue detected.")
        elif severity == "medium":
            score -= 20
            reasons.append("Medium severity issue detected.")
        elif severity == "low":
            score -= 5
            reasons.append("Low severity issue detected.")

    # ----------------------------
    # Structural change checks
    # ----------------------------
    if len(fixed_lines) < len(original_lines) * 0.5:
        score -= 20
        reasons.append("Fixed code is much shorter than original.")

    if "return" in original_code and "return" not in fixed_code:
        score -= 30
        reasons.append("Return statements may have been removed.")

    if "except:" in original_code and "except:" not in fixed_code:
        # This is usually good, but still risky.
        score -= 5
        reasons.append("Bare except was modified, verify correctness.")

    # ----------------------------
    # String literal mutation check
    # ----------------------------
    # If the fix changed the contents of string literals, the agent may have
    # over-edited — e.g. a false-positive heuristic rewrote text inside a string.
    # This is a behavioral change that a human must verify.
    _STRING_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
    original_strings = set(_STRING_RE.findall(original_code))
    fixed_strings = set(_STRING_RE.findall(fixed_code))
    if original_strings and (original_strings - fixed_strings):
        score -= 25
        reasons.append("Fix altered string literal contents — possible over-edit or false positive.")

    # ----------------------------
    # Clamp score
    # ----------------------------
    score = max(0, min(100, score))

    # ----------------------------
    # Risk level
    # ----------------------------
    if score >= 75:
        level = "low"
    elif score >= 40:
        level = "medium"
    else:
        level = "high"

    # ----------------------------
    # Auto-fix policy
    # ----------------------------
    # A low risk score is necessary but not sufficient. If the agent detected
    # any Medium or High severity issue, a human should verify the fix even
    # when the score is technically in the "low" band.
    has_significant_issues = any(
        str(issue.get("severity", "")).lower() in {"medium", "high"}
        for issue in issues
    )
    should_autofix = level == "low" and not has_significant_issues

    if not reasons:
        reasons.append("No significant risks detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "should_autofix": should_autofix,
    }
