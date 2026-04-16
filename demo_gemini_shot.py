"""Take a single screenshot of Gemini mode running on flaky_try_except.py."""
import time
from playwright.sync_api import sync_playwright

CODE = """\
def load_data(path):
    try:
        data = open(path).read()
    except:
        return None
    return data
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()

    page.goto("http://localhost:8501")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Switch to Gemini mode
    page.locator('[data-testid="stSelectbox"]').first.click()
    time.sleep(0.5)
    page.get_by_role("option", name="Gemini (requires API key)").click()
    time.sleep(1)

    # Paste code
    page.locator("textarea").first.fill(CODE)
    time.sleep(0.5)

    # Run
    page.get_by_role("button", name="Run BugHound").click()
    page.wait_for_selector("text=Agent trace", timeout=30000)
    time.sleep(2)

    page.screenshot(path="demo/08_gemini_in_action.png", full_page=True)
    print("Saved: demo/08_gemini_in_action.png")
    browser.close()
