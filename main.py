import importlib
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Import our customized core modules
from core.config_loader import load_config
from core.audio_engine import record_with_vad, transcribe_audio_array
from core.browser_engine import launch_monitored_chrome, send_message_via_browser

def main():
    # 1. Boot up configurations dynamically from TOML
    config = load_config()
    audio_cfg = config.get("audio", {})
    
    device_idx = audio_cfg.get("input_device_index", 2)
    sample_rate = audio_cfg.get("sample_rate", 16000)
    chrome_path = config.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    ica_url = config.get("ICA_URL", "https://japan.ica.ibm.com/ica/curatorai/apps/ui/new-chat/")
    
    r = sr.Recognizer()

    print("=== INITIALIZING BROWSER-INTEGRATED TRANSLATOR SYSTEM ===")

    # 2. Spawn Chrome via Browser Engine
    proc = launch_monitored_chrome(chrome_path, ica_url)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]

            if page.url != ica_url:
                page.goto(ica_url)

        except Exception as e:
            print(f"❌ Could not link console to browser session: {e}")
            proc.terminate()
            return

        print("\n==========================================================")
        print("1. Complete IBM SSO login.")
        print("2. Open a fresh ICA chat.")
        print("3. Click + then Insert Assistant & Agent.")
        print("4. Select RIE Assistant.")
        print("==========================================================")

        input("\nPress ENTER once ICA is ready...")
        print("\nTranslator attached successfully. Automatic listening has started.\n")

        try:
            while True:
                # 3. Capture audio streams via Audio Engine
                client_audio = record_with_vad(device_idx=device_idx, sample_rate=sample_rate)
                if client_audio is None:
                    continue

                print("[PROCESSING] Transcribing...")

                # 4. Process Speech-to-Text translation triggers
                client_text = transcribe_audio_array(client_audio, r, language_code="ja-JP", sample_rate=sample_rate)
                if not client_text:
                    continue
                
                print("\nTranscribed message sent to ICA Assistant.")
                client_payload = f"/c\n---\n{client_text}"

                print("\nRIE is translating it...")
                
                # 5. Hand over final strings back into active browser contexts
                send_message_via_browser(page, client_payload)
                print("\nTranslation success! Check the ICA output and use /r for your reply.\n")

        except KeyboardInterrupt:
            print("\nStopping translator pipelines...")

        browser.close()
        proc.terminate()

if __name__ == "__main__":
    main()