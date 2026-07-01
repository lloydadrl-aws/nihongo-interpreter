import os
import sys
import time
import tomllib
import numpy as np
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Core Environment Mapping
CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
ICA_URL = "https://japan.ica.ibm.com/ica/curatorai/apps/ui/new-chat/?assistant_id=a45c2bb4-6033-471d-94e0-0a2074084822"

def load_config():
    try:
        with open("config.toml", "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print("Error: config.toml not found.")
        sys.exit(1)

def transcribe_audio_array(audio_array, recognizer, language_code, sample_rate=16000):
    import io
    if audio_array is None: return None
    wav_io = io.BytesIO()
    sf.write(wav_io, audio_array, sample_rate, format='WAV', subtype='PCM_16')
    wav_io.seek(0)
    with sr.AudioFile(wav_io) as source:
        audio_file_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_file_data, language=language_code)
    except Exception:
        print("❌ [STT Error]: Speech could not be decoded.")
        return None

def send_message_via_browser(page, payload_text):
    """Send a message to ICA and return the translated response."""
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

        start_marker = "=== TRANSLATION START ==="
        end_marker = "=== TRANSLATION END ==="

        bubble_selectors = (
            "div[class*='message-content'], "
            "div[class*='markdown'], "
            "div[class*='bubble'], "
            "div[class*='streaming']"
        )

        max_attempts = 100
        translation = ""

        for _ in range(max_attempts):
            time.sleep(0.1)

            elements = page.query_selector_all(bubble_selectors)
            if not elements:
                continue

            recent_texts = [
                el.inner_text().strip()
                for el in elements[-2:]
                if el.inner_text().strip()
            ]

            if not recent_texts:
                continue

            active_block = ""

            for text in reversed(recent_texts):
                if start_marker in text or end_marker in text:
                    active_block = text
                    break

            if not active_block:
                continue

            if start_marker in active_block:
                translation = active_block.split(start_marker, 1)[1]
            else:
                translation = active_block

            if "Translated version:" in translation:
                translation = translation.split("Translated version:", 1)[1]

            if end_marker in translation:
                translation = translation.split(end_marker, 1)[0]

            translation = translation.strip()

            if end_marker in active_block:
                return translation

        return translation

    except Exception as e:
        return f"[Browser Interaction Error]: {e}"

def record_with_vad(
    device_idx,
    sample_rate=16000,
    threshold=0.01,
    silence_duration=2,
    block_size=1024
):
    """
    Automatically records speech.
    Starts when audio exceeds the threshold.
    Stops after silence_duration seconds of silence.
    """

    print("🎤 Listening for client...")
    print(f"\nPress Ctrl+C to end the program.")

    audio_chunks = []
    recording = False
    silence_blocks = 0

    max_silence_blocks = int(
        silence_duration * sample_rate / block_size
    )

    with sd.InputStream(
        samplerate=sample_rate,
        device=device_idx,
        channels=1,
        dtype="float32",
        blocksize=block_size
    ) as stream:

        while True:

            data, overflow = stream.read(block_size)

            if overflow:
                print("Audio overflow detected.")

            # Calculate RMS volume
            volume = np.sqrt(np.mean(np.square(data)))

            if not recording:

                # Wait until someone starts speaking
                if volume > threshold:
                    print("🟢 Speech detected.\n⏺️  Recording on going. ")
                    recording = True
                    audio_chunks.append(data.copy())

            else:

                audio_chunks.append(data.copy())

                if volume < threshold:
                    silence_blocks += 1
                else:
                    silence_blocks = 0

                if silence_blocks >= max_silence_blocks:
                    print("🔴 Speech ended.\n")
                    break

    if not audio_chunks:
        return None

    return np.concatenate(audio_chunks, axis=0)

def main():
    config = load_config()
    device_idx = config.get("audio", {}).get("input_device_index", 2)
    sample_rate = config.get("audio", {}).get("sample_rate", 16000)
    r = sr.Recognizer()

    print("=== INITIALIZING BROWSER-INTEGRATED TRANSLATOR SYSTEM ===")

    # Launch Chrome with remote debugging
    user_data_dir = os.path.join(
        os.environ.get("USERPROFILE", "C:"), "Temp", "pw-profile"
    )

    import subprocess
    proc = subprocess.Popen([
        str(CHROME),
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        ICA_URL
    ])

    time.sleep(3)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]

            if page.url != ICA_URL:
                page.goto(ICA_URL)

        except Exception as e:
            print(f"Could not link console to browser session: {e}")
            proc.terminate()
            return

        print("\n==========================================================")
        print("1. Complete IBM SSO login.")
        print("2. Open a fresh ICA chat.")
        print("==========================================================")

        input("\nPress ENTER once ICA is ready...")

        print("\nTranslator attached successfully.")
        print("Automatic listening has started.")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:

                # Automatically waits until someone speaks
                client_audio = record_with_vad(
                    device_idx=device_idx,
                    sample_rate=sample_rate
                )

                if client_audio is None:
                    continue

                print("[PROCESSING] Transcribing...")

                client_text = transcribe_audio_array(
                    client_audio,
                    r,
                    language_code="ja-JP",
                    sample_rate=sample_rate
                )

                if not client_text:
                    continue

                print(f"\n🎤 Client: {client_text}")

                client_payload = (
                    "/c\n---\n"
                    f"{client_text}"
                )

                print("\nRIE is translating it...")

                translation = send_message_via_browser(
                    page,
                    client_payload
                )

                print("\n================ TRANSLATION ================")
                print(translation)
                print("=============================================\n")

        except KeyboardInterrupt:
            print("\nStopping translator...")

        browser.close()
        proc.terminate()

if __name__ == "__main__":
    main()