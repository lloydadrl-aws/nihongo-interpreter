import sounddevice as sd

print("\n================ AVAILABLE AUDIO DEVICES ================")
devices = sd.query_devices()
for idx, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"Index [{idx}]: {device['name']} (Channels: {device['max_input_channels']})")
print("=========================================================\n")
print("👉 Copy the Index number of your microphone or VB-Cable into config.toml")