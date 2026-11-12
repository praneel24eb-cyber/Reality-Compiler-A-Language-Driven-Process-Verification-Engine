"""Browser acceptance checks against a synthetic Streamlit component fixture.

Run: python tests/browser_check.py [--browser-path PATH] [--output DIRECTORY]
Uses an isolated port and never connects to the production API or account.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-path")
    parser.add_argument("--output", default=".local/browser-results")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (output / "streamlit.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "tests/canvas_preview.py",
             "--server.port", str(port), "--server.address", "127.0.0.1",
             "--server.headless", "true"], cwd=root,
            env={**os.environ, "PYTHONPATH": str(root)}, stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError("Fixture server exited; see streamlit.log")
                    time.sleep(.2)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.browser_path)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{port}")
                node = page.get_by_role("button", name="Receive", exact=True)
                expect(node).to_be_visible(timeout=30000)
                node.focus()
                page.keyboard.press("Enter")
                expect(page.locator(".details").first).to_contain_text("The clerk receives the request.")
                assert page.locator("path.connection").count() == 5
                assert page.locator(".workflow path.connection").evaluate_all("els => new Set(els.map(e=>e.getAttribute('d'))).size") == 3
                handle = page.get_by_label("Review flow. Drag or use arrow keys to move.")
                handle.focus()
                page.keyboard.press("ArrowDown")
                expect(page.locator(".card.workflow")).to_have_css("top", "40px")
                page.get_by_role("button", name="Zoom out", exact=True).click()
                assert page.locator(".world").evaluate("el=>getComputedStyle(el).transform") != "matrix(1, 0, 0, 1, 0, 0)"
                page.get_by_role("button", name="Reset view", exact=True).click()
                page.get_by_label("Message to AI").fill("Explain this exact query")
                page.get_by_role("button", name="Send message", exact=False).click()
                expect(page.locator(".message.user")).to_have_count(1)
                expect(page.locator(".message.user")).to_contain_text("Explain this exact query")
                expect(page.locator(".message.assistant").last).to_contain_text("manager reviews it")
                expect(page.locator(".card.workflow")).to_have_css("top", "40px")
                page.get_by_role("button", name="Fit board", exact=True).click()
                expect(page.get_by_role("button", name="Procurement", exact=True)).to_be_in_viewport()
                page.screenshot(path=output / "desktop.png", full_page=True)
                page.get_by_role("button", name="Reset view", exact=True).click()
                page.set_viewport_size({"width": 390, "height": 844})
                expect(page.locator(".canvas-root")).to_have_class("canvas-root compact")
                expect(page.get_by_role("button", name="Zoom in", exact=True)).to_be_hidden()
                page.get_by_role("heading", name="AI Canvas", exact=True).scroll_into_view_if_needed()
                page.screenshot(path=output / "mobile-top.png", full_page=True)
                page.get_by_role("button", name="Receive", exact=True).click()
                expect(page.locator(".details").first).to_contain_text("The clerk receives the request.")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=output / "mobile.png", full_page=True)
                page.locator(".card.mindmap").get_by_role("button", name="Remove", exact=True).click()
                expect(page.locator(".card.mindmap")).to_have_count(0)
                expect(page.locator(".card.workflow")).to_have_count(1)
                expect(page.locator(".message.user")).to_have_count(1)
                assert not errors, errors
                browser.close()
            print("PASS: evidence, keyboard move, parallel/loop edges, zoom, query, persisted layout, fit, mobile, removal; no browser errors")
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    main()
