import os
import time
import subprocess
from playwright.sync_api import sync_playwright


def launch_monitored_chrome(chrome_path, target_url):
    """Spawns an instance of Google Chrome with explicit remote debugging hooks enabled."""
    user_data_dir = os.path.join(
        os.environ.get("USERPROFILE", "C:"), "Temp", "pw-profile"
    )

    proc = subprocess.Popen([
        str(chrome_path),
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        target_url
    ])
    time.sleep(3)
    return proc


def send_message_via_browser(page, payload_text):
    """
    Injects and submits payloads into ICA's chat box. Does NOT wait for a
    response — call wait_for_ica_response() afterward if you need to know
    when ICA has finished replying.
    Returns True if the message was submitted, False on error.
    """
    try:
        chat_box_selector = (
            "textarea, [placeholder*='type'], "
            "[placeholder*='message'], [contenteditable='true']"
        )
        page.wait_for_selector(chat_box_selector, timeout=10000)
        page.click(chat_box_selector)
        page.fill(chat_box_selector, payload_text)
        time.sleep(0.15)
        page.press(chat_box_selector, "Enter")
        return True
    except Exception as e:
        print(f"❌ [Browser Interaction Error]: {e}")
        return False


BUBBLE_SELECTORS = (
    "div[class*='message-content'], "
    "div[class*='markdown'], "
    "div[class*='bubble'], "
    "div[class*='streaming']"
)


def count_response_bubbles(page):
    """Counts current response bubble elements on the page. Reads no text content."""
    elements = page.query_selector_all(BUBBLE_SELECTORS)
    return len(elements)


def wait_for_ica_response(page, before_count, max_attempts=100, poll_interval=0.1):
    """
    Presence-only check: waits until the number of response bubbles on the
    page increases beyond before_count, meaning ICA has produced a new
    output. Does NOT read, store, or inspect the text content of that output —
    only whether a new bubble exists.

    Returns True once a new bubble is detected, False if it timed out
    (max_attempts * poll_interval seconds).
    """
    for _ in range(max_attempts):
        time.sleep(poll_interval)

        if count_response_bubbles(page) > before_count:
            return True

    print("⚠️ Timed out waiting for ICA response — proceeding anyway.")
    return False