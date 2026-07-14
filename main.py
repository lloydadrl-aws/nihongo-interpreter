import os
import sys
import time
import argparse
import threading
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Core components
from core.config_loader import load_config, load_audio_source_config
from core.browser_engine import launch_monitored_chrome, send_message_via_browser

# Clean pipeline imports
import core.pipeline_workers as workers
from core.pipeline_workers import audio_queue, text_queue


def resolve_active_source(config):
    """Determines audio source with precedence: CLI flag > env var > config file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["mic", "meeting_app"], default=None,
                         help="Override the audio source for this run.")
    args, _ = parser.parse_known_args()

    if args.source:
        print(f"🔧 Source overridden via CLI flag: {args.source}")
        return args.source

    env_source = os.environ.get("AUDIO_SOURCE")
    if env_source in ("mic", "meeting_app"):
        print(f"🔧 Source overridden via AUDIO_SOURCE env var: {env_source}")
        return env_source

    return config.get("audio", {}).get("source", "mic")


def main():
    config = load_config()
    active_source = resolve_active_source(config)
    audio_settings = load_audio_source_config(config, active_source)

    chrome_cfg = config.get("chrome", {})
    ica_cfg = config.get("ICA_URL", {})

    chrome_path = chrome_cfg.get("chrome_path", "")
    ica_url = ica_cfg.get("base_url", "")

    recognizer = sr.Recognizer()

    print(f"=== INITIALIZING BROWSER-INTEGRATED TRANSLATOR SYSTEM (source: {active_source}) ===")
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
            args=(
                audio_settings["device_idx"],
                audio_settings["sample_rate"],
                audio_settings["silence_duration"],
                audio_settings["threshold"],
            ),
            daemon=True
        ).start()

        threading.Thread(
            target=workers.audio_processor_worker,
            args=(recognizer, "ja-JP", audio_settings["sample_rate"]),
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