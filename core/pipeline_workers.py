import queue
import speech_recognition as sr
from core.audio_engine import record_with_vad, transcribe_audio_array

# Thread-safe queues shared across the entire system
audio_queue = queue.Queue()
text_queue = queue.Queue()

# Global shutdown state
running = True


def audio_recording_worker(device_idx, sample_rate, silence_duration, threshold=0.01):
    """THREAD 1: Continuously records audio blocks in the background."""
    print("🎧 Continuous audio tracking initialized...\n")
    input_counter = 1

    while running:
        try:
            client_audio = record_with_vad(
                device_idx=device_idx,
                sample_rate=sample_rate,
                silence_duration=silence_duration,
                threshold=threshold,
            )

            if client_audio is not None and running:
                print(f"📥 Audio input {input_counter} captured! Appending to processing queue.\n")
                audio_queue.put((input_counter, client_audio))
                input_counter += 1
        except Exception as e:
            print(f"❌ Recording thread stopped unexpectedly: {e}")
            break


def audio_processor_worker(recognizer, language_code, sample_rate):
    """THREAD 2: Background worker handling speech-to-text processing."""
    while running:
        try:
            input_number, audio_data = audio_queue.get(timeout=1)
        except queue.Empty:
            continue

        print(f"\n[PROCESSING] Transcribing input {input_number} in background...\n")
        client_text = transcribe_audio_array(audio_data, recognizer, language_code=language_code, sample_rate=sample_rate)

        if client_text and client_text.strip():
            client_payload = f"/c\n{client_text}"
            text_queue.put((input_number, client_payload))
        else:
            print(f"⚠️ Transcription {input_number} empty or failed.")

        audio_queue.task_done()