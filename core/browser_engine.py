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
    """Injects and submits payloads safely into target browser chat nodes."""
    try:
        chat_box_selector = (
            "textarea, [placeholder*='type'], "
            "[placeholder*='message'], [contenteditable='true']"
        )
        page.wait_for_selector(chat_box_selector, timeout=10000)
        page.click(chat_box_selector)
        page.fill(chat_box_selector, payload_text)
        time.sleep(0.1)
        page.press(chat_box_selector, "Enter")
    except Exception as e:
        print(f"❌ [Browser Interaction Error]: {e}")