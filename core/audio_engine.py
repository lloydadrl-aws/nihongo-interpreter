import io
import numpy as np
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr

def record_with_vad(device_idx, sample_rate=16000, silence_duration=3, threshold=0.01,
                     block_size=1024, min_duration_sec=0.4, trim_padding_sec=0.25):
    """
    Automatically tracks and records speech.
    Starts capturing when audio exceeds the threshold, stops after quiet thresholds.

    trim_padding_sec: how much of the trailing silence run to KEEP (not delete) when
    a cutoff is triggered. Japanese speech often ends in devoiced (whispered) vowels
    that are quiet enough to count as "silence" blocks — trimming the full silence
    run can delete these real syllables along with the true dead air. Keeping a small
    buffer preserves the tail of speech while still discarding the true pause.
    """
    print("=============================")
    print("🎧 Listening...")
    print("\nPress Ctrl+C to exit.")

    audio_chunks = []
    recording = False
    silence_blocks = 0

    max_silence_blocks = int(silence_duration * sample_rate / block_size)
    padding_blocks = int(trim_padding_sec * sample_rate / block_size)

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
                print("⚠️ Audio overflow detected.")

            # Calculate Root Mean Square (RMS) volume
            volume = np.sqrt(np.mean(np.square(data)))

            if not recording:
                if volume > threshold:
                    print("🟢 Speech detected.\n⏺️  Recording ongoing...")
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
                    trim_blocks = max(0, silence_blocks - padding_blocks)
                    if trim_blocks > 0:
                        audio_chunks = audio_chunks[:-trim_blocks]
                    break

    if not audio_chunks:
        return None

    # Reject very short bursts (notification dings, clicks, pops) before they
    # ever reach the STT queue
    duration_sec = len(audio_chunks) * block_size / sample_rate
    if duration_sec < min_duration_sec:
        print(f"🔇 Discarded short burst ({duration_sec:.2f}s) — likely a notification sound, not speech.")
        return None

    return np.concatenate(audio_chunks, axis=0)


def transcribe_audio_array(audio_array, recognizer, language_code="ja-JP", sample_rate=16000):
    """Converts recorded raw numpy arrays into clean digital text lines via STT engines."""
    if audio_array is None:
        return None

    wav_io = io.BytesIO()
    sf.write(wav_io, audio_array, sample_rate, format='WAV', subtype='PCM_16')
    wav_io.seek(0)

    with sr.AudioFile(wav_io) as source:
        audio_file_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_file_data, language=language_code)
    except Exception:
        print("\n❌ [STT Error]: Speech could not be decoded.\n")
        return None