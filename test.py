import os
import sys
import time
import tomllib
import numpy as np
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
from pathlib import Path
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

def record_manual_toggle(device_idx, sample_rate=16000):
    print("🔴 RECORDING STARTED... Press [ENTER] again to stop recording.")
    audio_data = []
    def callback(indata, frames, time, status):
        if status: print(status, file=sys.stderr)
        audio_data.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, device=device_idx, channels=1, callback=callback):
        input() 
        
    print("⬜ RECORDING STOPPED.")
    if len(audio_data) == 0: return None
    return np.concatenate(audio_data, axis=0)

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
    """Types text, then renders each distinct translation section header and content dynamically as it streams."""
    try:
        # 1. Target and fill input text box
        chat_box_selector = "textarea, [placeholder*='type'], [placeholder*='message'], [contenteditable='true']"
        page.wait_for_selector(chat_box_selector, timeout=10000)
        
        page.click(chat_box_selector)
        page.fill(chat_box_selector, payload_text)
        time.sleep(0.15)
        
        # Determine target segment rules
        is_reply = "ReplyOfTheUser" in payload_text
        start_marker = "=== REPLY START ===" if is_reply else "=== TRANSLATION START ==="
        end_marker = "=== REPLY END ===" if is_reply else "=== TRANSLATION END ==="
        
        # Section markers matching prompt
        section_tags = ["[ENGLISH]", "[JAPANESE]", "[ROMAJI]"]
        display_headers = {
            "[ENGLISH]": "================ Translated Version ================",
            "[JAPANESE]": "\n================ Original Message =================",
            "[ROMAJI]": "\n==================== Romaji ========================"
        }
        
        # 2. Fire transmission down browser pipeline
        page.press(chat_box_selector, "Enter")
        print("Payload sent. Streaming response sections live...\n")
        
        # 3. High-Frequency Streaming Parser Loop
        latest_full_text = ""
        stable_cycles = 0
        max_attempts = 150  
        
        current_section_idx = -1
        printed_content_by_section = {tag: "" for tag in section_tags}
        
        # Expanded selector list to ensure we grab the generation bubble immediately
        bubble_selectors = "div[class*='message-content'], div[class*='markdown'], div[class*='bubble'], div[class*='streaming']"
        
        for attempt in range(max_attempts):
            time.sleep(0.1)  # Faster polling (100ms instead of 200ms) for true real-time feel
            
            elements = page.query_selector_all(bubble_selectors)
            if not elements:
                continue
            
            # Extract text from the last few elements to ensure we catch the live generation stream
            recent_texts = [el.inner_text().strip() for el in elements[-3:] if el.inner_text().strip()]
            active_block = ""
            
            # Find the bubble that actually contains our translation content
            for text_block in reversed(recent_texts):
                if "Translated version:" in text_block or start_marker in text_block:
                    active_block = text_block
                    break
            
            if not active_block and recent_texts:
                active_block = recent_texts[-1]

            # --- AGGRESSIVE STREAMING PARSER ---
            # Clean up the block text regardless of whether the start marker has completely finished rendering
            normalized_block = active_block
            if start_marker in normalized_block:
                normalized_block = normalized_block.split(start_marker)[-1]
            if end_marker in normalized_block:
                normalized_block = normalized_block.split(end_marker)[0]
            
            normalized_block = normalized_block.strip()

            # Process our content tags sequentially
            for idx, tag in enumerate(section_tags):
                if tag in normalized_block:
                    # Isolate text after the section header label
                    sub_content = normalized_block.split(tag)[-1]
                    
                    # Prevent bleeding into future sections
                    for next_tag in section_tags[idx+1:]:
                        if next_tag in sub_content:
                            sub_content = sub_content.split(next_tag)[0]
                    sub_content = sub_content.strip()
                    
                    # Print the stylized header banner the millisecond the section tag is spotted
                    if idx > current_section_idx:
                        current_section_idx = idx
                        sys.stdout.write(f"\n{display_headers[tag]}\n")
                        sys.stdout.flush()
                    
                    # Calculate character-by-character delta stream
                    already_printed = printed_content_by_section[tag]
                    if sub_content.startswith(already_printed) and len(sub_content) > len(already_printed):
                        new_text = sub_content[len(already_printed):]
                        sys.stdout.write(new_text)
                        sys.stdout.flush()
                        printed_content_by_section[tag] = sub_content
            
            # Stop loop conditions
            if end_marker in active_block:
                latest_full_text = active_block
                break
                
            if active_block == latest_full_text and len(active_block) > 5:
                stable_cycles += 1
                if stable_cycles >= 15: # ~1.5 seconds of stillness
                    latest_full_text = active_block
                    break
            else:
                stable_cycles = 0
                latest_full_text = active_block

        print("\n\n=============================================================")
        
        # Clean fallback extraction formatting for meeting session log files
        if latest_full_text and start_marker in latest_full_text:
            try:
                inner_content = latest_full_text.split(start_marker)[-1].split(end_marker)[0].strip()
                return inner_content
            except Exception:
                pass
        return latest_full_text.replace(start_marker, "").replace(end_marker, "").strip()
        
    except Exception as e:
        return f"[Browser Interaction Error]: {e}"

def record_with_vad(
    device_idx,
    sample_rate=16000,
    threshold=0.01,
    silence_duration=3.0,
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
                    print("🟢 Speech detected.")
                    recording = True
                    audio_chunks.append(data.copy())

            else:

                audio_chunks.append(data.copy())

                if volume < threshold:
                    silence_blocks += 1
                else:
                    silence_blocks = 0

                if silence_blocks >= max_silence_blocks:
                    print("🔴 Speech ended.")
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
                    "[Input Type: ExtractedAudioConverted]\n"
                    f"Content: {client_text}"
                )

                print("Sending transcript to ICA...")

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