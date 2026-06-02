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
    """Types text and instantly streams/extracts data the millisecond the end marker hits the DOM."""
    try:
        # 1. Target and fill input text box
        chat_box_selector = "textarea, [placeholder*='type'], [placeholder*='message'], [contenteditable='true']"
        page.wait_for_selector(chat_box_selector, timeout=10000)
        
        page.click(chat_box_selector)
        page.fill(chat_box_selector, payload_text)
        time.sleep(0.15) # Shaved down typing delay
        
        # Determine target end markers
        is_reply = "ReplyOfTheUser" in payload_text
        start_marker = "=== REPLY START ===" if is_reply else "=== TRANSLATION START ==="
        end_marker = "=== REPLY END ===" if is_reply else "=== TRANSLATION END ==="
        
        # 2. Fire transmission down browser pipeline
        page.press(chat_box_selector, "Enter")
        print("Payload sent. Optimistic live tracking active...")
        
        # 3. High-frequency polling loop (Checks every 200ms instead of 500ms)
        latest_text = ""
        stable_cycles = 0
        max_attempts = 100  # 100 * 0.2s = 20 seconds max timeout safety net
        
        bubble_selectors = "div[class*='message-content'], div[class*='markdown'], div[class*='bubble']"
        
        for attempt in range(max_attempts):
            time.sleep(0.2)  # High-speed sampling rate
            
            elements = page.query_selector_all(bubble_selectors)
            if not elements:
                continue
            
            # Isolate the last two message frames
            recent_texts = [el.inner_text().strip() for el in elements[-2:] if el.inner_text().strip()]
            
            active_block = ""
            for text_block in reversed(recent_texts):
                if start_marker in text_block or end_marker in text_block:
                    active_block = text_block
                    break
            
            if not active_block and recent_texts:
                active_block = recent_texts[-1]
                if "[Input Type:" in active_block and len(recent_texts) > 1:
                    active_block = recent_texts[-2]
            
            # ⚡ INSTANT EXIT: The moment the end tag is detected, stop waiting immediately!
            if end_marker in active_block:
                latest_text = active_block
                break
                
            # Fallback text stability check (requires only 1 second of stability now)
            if active_block == latest_text and len(active_block) > 5:
                stable_cycles += 1
                if stable_cycles >= 5: # 5 * 0.2s = 1 second of freeze time
                    break
            else:
                stable_cycles = 0
                latest_text = active_block

        # 4. Parse and return multi-line structure
        if latest_text and start_marker in latest_text:
            try:
                inner_content = latest_text.split(start_marker)[-1].split(end_marker)[0].strip()
                lines = [line.strip() for line in inner_content.split('\n')]
                return "\n".join(lines)
            except Exception:
                pass
                
        return latest_text.replace(start_marker, "").replace(end_marker, "").strip()
        
    except Exception as e:
        return f"[Browser Interaction Error]: {e}"

def main():
    config = load_config()
    device_idx = config.get("audio", {}).get("input_device_index", 2)
    sample_rate = config.get("audio", {}).get("sample_rate", 16000)
    r = sr.Recognizer()

    print("=== INITIALIZING BROWSER-INTEGRATED TRANSLATOR SYSTEM ===")
    
    # 🌟 FORCE THE BROWSER INITIALIZATION PROFILE SPACE
    user_data_dir = os.path.join(os.environ.get("USERPROFILE", "C:"), "Temp", "pw-profile")
    import subprocess
    proc = subprocess.Popen([
        str(CHROME), "--remote-debugging-port=9222", f"--user-data-dir={user_data_dir}", ICA_URL
    ])
    time.sleep(3)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            
            # 🌟 EXTRA SAFE GUARD: Force page to navigate fresh to the clean landing URL room
            if page.url != ICA_URL:
                page.goto(ICA_URL)
                
        except Exception as e:
            print(f"Could not link console to browser session: {e}")
            proc.terminate()
            return

        print("\n==========================================================")
        print("👉 INITIAL AUTHENTICATION SELECTION:")
        print("1. Complete your single sign-on steps inside Chrome.")
        print("2. Ensure a fresh, completely blank chat window is open.")
        print("==========================================================")
        input("\n👉 Once your clean agent room is ready, press [ENTER] HERE to attach...")
        
        print("\nConsole successfully attached. Ready for live client monitoring!\n")
        
        while True:
            print("\n" + "="*60)
            input("👉 Press [ENTER] to start recording the Client's Japanese Audio...")
            
            client_audio = record_manual_toggle(device_idx, sample_rate)
            print("[PROCESSING] Decoding client transcript stream...")
            client_text = transcribe_audio_array(client_audio, r, language_code="ja-JP", sample_rate=sample_rate)
            
            if not client_text: continue
            print(f"▶️ Captured Raw Text: {client_text}")
            
            client_payload = f"[Input Type: ExtractedAudioConverted]\nContent: {client_text}"
            print("Injecting securely via browser session layer...")
            
            agent_translation = send_message_via_browser(page, client_payload)
            print("\n================= CLIENT SPEECH TRANSLATION =================")
            print(agent_translation)
            print("=============================================================\n")
            
            print("Now prepare your response to the client.")
            user_input_text = input("👉 Type your English reply here and press [ENTER]: ")
            
            if not user_input_text.strip(): continue
            if user_input_text.lower() == 'exit': break
                
            user_payload = f"[Input Type: ReplyOfTheUser]\nContent: {user_input_text}"
            print("\nSubmitting reply format down browser layer...")
            
            agent_reply = send_message_via_browser(page, user_payload)
            print("\n=================== YOUR GENERATED JAPANESE REPLY ===================")
            print(agent_reply)
            print("=====================================================================\n")

        browser.close()
        proc.terminate()

if __name__ == "__main__":
    main()