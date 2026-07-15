import sys
import sounddevice as sd

# Smart fallback configuration check
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_config():
    """Loads and returns the project TOML configuration framework safely."""
    try:
        with open("config.toml", "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print("❌ Error: config.toml not found. Please create one based on the documentation templates.")
        sys.exit(1)

def resolve_device(name_substring, kind="input"):
    """Find a device index by matching part of its name (case-insensitive)."""
    devices = sd.query_devices()
    matches = []
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0 and name_substring.lower() in device['name'].lower():
            matches.append((idx, device))

    if not matches:
        available = "\n".join(f"  [{i}] {d['name']}" for i, d in enumerate(devices) if d['max_input_channels'] > 0)
        print(f"❌ No input device matching '{name_substring}' found.\nAvailable input devices:\n{available}")
        sys.exit(1)

    if len(matches) > 1:
        print(f"⚠️ Multiple devices match '{name_substring}', using the first: {matches[0][1]['name']}")

    idx, device = matches[0]
    print(f"🎙️  Resolved '{name_substring}' → [{idx}] {device['name']}")
    return idx


def load_audio_source_config(config, source):
    """
    Resolves the active audio source's device index and settings from config.
    `source` should be 'mic' or 'meeting_app'.
    """
    audio_cfg = config.get("audio", {})
    device_name = audio_cfg.get("devices", {}).get(source)

    if not device_name:
        print(f"❌ No device name configured for source '{source}' under [audio.devices].")
        sys.exit(1)

    device_idx = resolve_device(device_name)

    source_cfg = audio_cfg.get(source, {})
    return {
        "device_idx": device_idx,
        "sample_rate": audio_cfg.get("sample_rate", 16000),
        "channels": audio_cfg.get("channels", 1),
        "silence_duration": source_cfg.get("silence_duration", audio_cfg.get("silence_duration", 1.5)),
        "threshold": source_cfg.get("threshold", 0.01),
    }