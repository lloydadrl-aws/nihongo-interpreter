# Japanese Meeting STT & Translation Assistant

An automated, real-time tool designed to capture Japanese audio, decode speech-to-text live via microphone/virtual audio routing, and securely stream live structural translations to your local terminal using a browser automation layer.

---

## Prerequisites

Before installing the application, ensure your machine has the following system dependencies installed:

1. **Python 3.12.+**: Ensure Python is added to your system environment `PATH` during installation.
2. **Google Chrome**: The browser tool hooks natively into your standard Google Chrome installation path.
3. **Audio Hardware Input**: A working microphone, or a virtual audio cable (like VB-Cable) if routing audio directly from a web meeting (Teams, Zoom, etc.).

---

## Quick Start Installation

### 1. Clone the Repository
```bash
git clone https://github.com/lloydadrl-aws/nihongo-interpreter
```

### 2. Set Up an Isolated Virtual Environment (venv)
You only need to do this one time only.

```bash
# cd within the repo
cd nihongo-interpreter

# Create the virtual environment
py -m venv venv

# Activate the environment (Windows)
.\venv\Scripts\activate

# Activate the environment (Mac/Linux)
source venv/bin/activate
```
*Note: The terminal should have (venv) at the left most display.*
``` (venv) C:\Users\lloyd.lindo\Desktop\... ```

### 3. Install python dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Playwright Web Drivers
```bash
playwright install
```

### 5. Audio Routing via VB-CABLE (Crucial for Virtual Meetings)

### A Note on Security & Data Privacy (VB-CABLE)
I recommend VB-AUDIO Virtual Cable because it is an industry-standard digital audio driver used globally by audio professionals.
* **Data Security:** It operates 100% offline. It does not have network access, nor does it log, collect, or transmit any meeting audio or data outside your local machine.
* **System Safety:** The installers are digitally signed by Microsoft and fully pass all enterprise-grade antivirus scans (0 flags on VirusTotal).

If you are translating audio from a live online meeting (Teams, Zoom, Webex, or a browser window) rather than using a physical microphone in the room, follow these steps:

1. **Install VB-CABLE:** Download and install the driver from [VB-Audio](https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip). *Note: A system restart is usually required after installation.*
2. **Extract Contents:** Extract the contents in the Zip somewhere, folder name does not matter. Then, install VBCABLE_Setup_x64 from the extracted contents.
3. **Configure your Meeting App:** Open your meeting software (e.g., Zoom, Teams, Google), next go to system sound settings -> volume mixer, and change the "Apps" **Output Device** to **CABLE Input (VB-Audio Virtual Cable)**.
4. **Configure CABLE Output Properties:** Go to System -> Sound -> Advanced -> More sound settings -> Recording tab -> CABLE Output -> Properties -> Listen tab -> Check Listen to this device -> Hit Apply -> Hit OK -> Close settings.

Now, any audio played in your meeting will drop straight into RIE-san's translator pipeline seamlessly!

### 5.1 Configuring Your Audio Devices (One-Time Setup)

Unlike earlier versions, you **no longer need to copy a numeric device index** into `config.toml`. The program now resolves your microphone and VB-Cable automatically by matching a name you provide against the devices Windows reports — this survives index changes caused by reboots, driver updates, or plugging/unplugging headsets.

You only need to tell the program *part* of each device's name, in `config.toml`:

```toml
[audio]
source = "mic"          # default source: "mic" or "meeting_app"
sample_rate = 16000
channels = 1
silence_duration = 1.5

[audio.devices]
mic = "Internal Microphone"
meeting_app = "CABLE Output (VB-Audio Virtual Cable)"

[audio.mic]
threshold = 0.01
silence_duration = 1.5

[audio.meeting_app]
threshold = 0.003
silence_duration = 1.0
```

**How to find the exact device name (if auto-matching fails):**

Run the diagnostic script once:
```bash
py find_device.py
```
Sample output:
```
================ AVAILABLE AUDIO DEVICES ================
Index [0]: Microsoft Sound Mapper - Input (Channels: 2)
Index [1]: Internal Microphone (Cirrus Log (Channels: 2)
Index [2]: CABLE Output (VB-Audio Virtual  (Channels: 16)
=========================================================
```
Copy the name text (not the index) shown for your device and paste it into `[audio.devices]` in `config.toml`. If more than one device matches your search string, the program will pick the first match and warn you in the console — in that case, use a longer, more specific portion of the name to disambiguate.

*Note: The `threshold` values above are starting points. `meeting_app` audio (via VB-Cable) is usually cleaner than mic input and needs a lower threshold — tune both if speech is being missed or notification sounds are triggering false captures.*

### 5.2 Switching Between Mic and Meeting Audio

You can set your default source once in `config.toml` (`source = "mic"` or `source = "meeting_app"`), and override it per-run without editing the file:

```bash
# Use the microphone for this run
run.bat --source mic

# Use VB-Cable / meeting audio for this run
run.bat --source meeting_app

# Or via environment variable
set AUDIO_SOURCE=meeting_app
run.bat
```

Precedence: **CLI flag > environment variable > config.toml default.**

---

## How to Run the App

Make sure every variable in `config.toml` has values.

For `chrome_path`, locate your Google Chrome browser path in your local device. Once located, perform `Ctrl + Shift + Right-click` then select `Copy as path`. After pasting the path into this variable, add black slashes `\` for each current back slash.

From `C:\Users\lloyd.lindo\Desktop\` to `C:\\Users\\lloyd.lindo\\Desktop\\`

For `silence_duration`, the program interprets this variable in seconds — it controls how long the program waits after speech stops before considering that input "finished" and sending it for transcription. Be cautious on what you set here.

*I recommend starting with 1.5 and testing against real speech. Adjust to fit your preference. Meeting audio (`meeting_app`) generally works well with a shorter value than a live mic.*

Click `run.bat` found in the project folder.

**The Single Sign-On (SSO) Step:** A Google Chrome browser window will automatically launch.

Complete your standard Single Sign-On steps inside the browser.

Navigate into your designated workspace room and ensure a fresh, completely blank assistant chat window is open.

Click the `+` sign in the chat and select **Insert Assistant & Agent**. Then select **RIE**.

Return to your terminal, press `[ENTER]`, and the system console will attach seamlessly!

Now let the program receive audio and do its job. Very short, non-speech sounds (like notification dings) are automatically filtered out before transcription, so they won't be sent to ICA.