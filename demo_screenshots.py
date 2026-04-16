"""
Run BugHound through all 7 test cases and save screenshots to demo/.
Usage: python demo_screenshots.py
"""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8501"
DEMO_DIR = "demo"

TEST_CASES = [
    {
        "name": "01_clean_code",
        "label": "Test 1 — Clean Code (No Issues)",
        "mode": "Heuristic only (no API)",
        "code": """\
import logging

def add(a, b):
    logging.info("Adding numbers")
    return a + b
""",
    },
    {
        "name": "02_bare_except",
        "label": "Test 2 — Bare Except (High Severity)",
        "mode": "Heuristic only (no API)",
        "code": """\
def load_data(path):
    try:
        data = open(path).read()
    except:
        return None
    return data
""",
    },
    {
        "name": "03_mixed_issues",
        "label": "Test 3 — All Three Heuristic Patterns",
        "mode": "Heuristic only (no API)",
        "code": """\
# TODO: Replace this with real input validation

def compute_ratio(x, y):
    print("computing ratio...")
    try:
        return x / y
    except:
        return 0
""",
    },
    {
        "name": "04_medium_severity_guardrail",
        "label": "Test 4 — Medium Severity Blocks Auto-Fix (Part 3 Guardrail)",
        "mode": "Heuristic only (no API)",
        "code": """\
def compute(x, y):
    # TODO: validate inputs
    return x / y
""",
    },
    {
        "name": "05_string_literal_guardrail",
        "label": "Test 5 — String Literal Mutation Blocked (Part 4 Guardrail)",
        "mode": "Heuristic only (no API)",
        "code": """\
def docs():
    msg = "use print() to debug"
    return msg
""",
    },
    {
        "name": "06_edge_case_comments_only",
        "label": "Test 6 — Edge Case: Comments Only",
        "mode": "Heuristic only (no API)",
        "code": """\
# This is just a comment
# TODO: do something useful here
""",
    },
]


def set_mode(page, mode_label):
    """Select the sidebar mode dropdown."""
    page.locator('[data-testid="stSelectbox"]').first.click()
    time.sleep(0.5)
    page.get_by_role("option", name=mode_label).click()
    time.sleep(0.8)


def clear_and_type_code(page, code):
    """Clear the text area and type new code."""
    textarea = page.locator("textarea").first
    textarea.click()
    textarea.fill(code)
    time.sleep(0.5)


def run_bughound(page):
    """Click Run BugHound and wait for results."""
    page.get_by_role("button", name="Run BugHound").click()
    # Wait for the Agent trace section to appear — signals workflow complete
    page.wait_for_selector("text=Agent trace", timeout=20000)
    time.sleep(1.5)  # let all panels render


def save_screenshot(page, name, label):
    path = f"{DEMO_DIR}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  Saved: {path}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    print("Opening BugHound...")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    for tc in TEST_CASES:
        print(f"\nRunning: {tc['label']}")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        set_mode(page, tc["mode"])
        clear_and_type_code(page, tc["code"])
        run_bughound(page)
        save_screenshot(page, tc["name"], tc["label"])

    # Test 7 — Gemini mode (screenshot sidebar warning only, no API call)
    print("\nRunning: Test 7 — Gemini Mode Sidebar Warning")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)
    set_mode(page, "Gemini (requires API key)")
    time.sleep(1)
    page.screenshot(path=f"{DEMO_DIR}/07_gemini_mode_warning.png", full_page=True)
    print(f"  Saved: {DEMO_DIR}/07_gemini_mode_warning.png")

    browser.close()
    print("\nAll screenshots saved to demo/")
