"""End-to-end check in a real browser (Chromium) against the running stack.

Opens the web interface through the HTTPS proxy, sends a message in the chat and
waits for the engine's answer. Every request made by the page is recorded: any
request to a host other than the stack itself fails the check (no third party).
Usage: python browser_check.py [https://localhost:8443] [chromium executable] [screenshot.png]
"""
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8443"
CHROMIUM = (sys.argv[2] or None) if len(sys.argv) > 2 else None
SHOT = sys.argv[3] if len(sys.argv) > 3 else "browser_check.png"
origin = urlparse(BASE).netloc
# A real model on a CPU can take minutes for the first answer.
TIMEOUT_MS = int(__import__("os").environ.get("BROWSER_CHECK_TIMEOUT_MS", "60000"))
requests, foreign = [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROMIUM) if CHROMIUM else p.chromium.launch()
    # The local CA is not installed in this throwaway browser profile.
    page = browser.new_context(ignore_https_errors=True, locale="fr-FR").new_page()

    def record(req):
        host = urlparse(req.url).netloc
        requests.append(req.url)
        if req.url.startswith(("http://", "https://", "ws://", "wss://")) and host != origin:
            foreign.append(req.url)

    page.on("request", record)
    page.goto(f"{BASE}/laurentia", wait_until="networkidle")
    page.get_by_test_id("composer-input").fill("Bonjour, réponds-moi en une phrase.")
    page.get_by_test_id("composer-submit").click()
    bubble = page.get_by_test_id("assistant-bubble").last
    bubble.wait_for(timeout=TIMEOUT_MS)
    page.wait_for_function(
        "() => { const b=[...document.querySelectorAll('[data-testid=assistant-bubble]')].pop();"
        " return b && b.innerText.trim().length > 20; }", timeout=TIMEOUT_MS)
    answer = bubble.inner_text()
    page.screenshot(path=SHOT, full_page=True)
    browser.close()

print(f"requests: {len(requests)}  foreign: {len(foreign)}")
for u in foreign:
    print("FOREIGN", u)
print("answer:", answer[:200].replace("\n", " "))
sys.exit(1 if foreign or not answer.strip() else 0)
