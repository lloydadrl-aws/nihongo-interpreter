import time
import threading
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Core components
from core.config_loader import load_config
from core.browser_engine import launch_monitored_chrome, send_message_via_browser

# Clean pipeline imports
import core.pipeline_workers as workers
from core.pipeline_workers import audio_queue, text_queue

def main():
    config = load_config()
    audio_cfg = config.get("audio", {})
    chrome_cfg = config.get("chrome", {})
    ica_cfg = config.get("ICA_URL", {})

    device_idx = audio_cfg.get("input_device_index", 2)
    sample_rate = audio_cfg.get("sample_rate", 16000)
    silence_duration = audio_cfg.get("silence_duration", 1.5) 
    chrome_path = chrome_cfg.get("chrome_path", "")
    ica_url = ica_cfg.get("base_url", "")

    recognizer = sr.Recognizer()

    print("=== INITIALIZING BROWSER-INTEGRATED TRANSLATOR SYSTEM ===")
    proc = launch_monitored_chrome(chrome_path, ica_url)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            page = browser.contexts[0].pages[0]
            if page.url != ica_url:
                page.goto(ica_url)
        except Exception as e:
            print(f"❌ Could not link console to browser session: {e}")
            proc.terminate()
            return

        print("\n==========================================================")
        print("1. Complete IBM SSO login. \n2. Open a fresh ICA chat.")
        print("3. Add RIE Assistant.")
        print("==========================================================")
        input("\nPress ENTER once ICA is ready...")
        print("\nTranslator attached successfully. Non-blocking pipelines running.\n")

        # 1. Start background workers via the pipeline module
        threading.Thread(
            target=workers.audio_recording_worker,
            args=(device_idx, sample_rate, silence_duration),
            daemon=True
        ).start()

        threading.Thread(
            target=workers.audio_processor_worker, 
            args=(recognizer, "ja-JP", sample_rate),
            daemon=True
        ).start()

        try:
            # 2. Main execution event loop handles browser typing
            while True:
                while not text_queue.empty():
                    input_number, payload_text = text_queue.get_nowait()
                    send_message_via_browser(page, payload_text)
                    print(f"🚀 Transcribed input {input_number} sent to ICA...\n")
                    text_queue.task_done()

                time.sleep(0.05)
                page.evaluate("() => {}") 

        except KeyboardInterrupt:
            print("\nStopping translator pipelines...")
            workers.running = False

        browser.close()
        proc.terminate()

if __name__ == "__main__":
    main()
