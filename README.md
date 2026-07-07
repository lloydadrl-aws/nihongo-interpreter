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

### 2. Audio Routing via VB-CABLE (Crucial for Virtual Meetings)

### A Note on Security & Data Privacy (VB-CABLE)
We recommend VB-AUDIO Virtual Cable because it is an industry-standard digital audio driver used globally by audio professionals. 
* **Data Security:** It operates 100% offline. It does not have network access, nor does it log, collect, or transmit any meeting audio or data outside your local machine.
* **System Safety:** The installers are digitally signed by Microsoft and fully pass all enterprise-grade antivirus scans (0 flags on VirusTotal).

If you are translating audio from a live online meeting (Teams, Zoom, Webex, or a browser window) rather than using a physical microphone in the room, follow these steps:

1. **Install VB-CABLE:** Download and install the driver from [[VB-Audio]([[https://vb-audio.com/Cable/](https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip)](https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip))](https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip). *Note: A system restart is usually required after installation.*
2. **Extract Contents:** Extract the contents in the Zip somewhere, folder name does not matter. Then, install VBCABLE_Setup_x64 from the extracted contents.
3. **Configure your Meeting App:** Open your meeting software (e.g., Zoom, Teams, Google), next go to system sound settings -> volume mixer, and change the "Apps" **Output Device** to **CABLE Input (VB-Audio Virtual Cable)**.

Now, any audio played in your meeting will drop straight into RIE-san's translator pipeline seamlessly!
### 2.1 Identifying Channel Index
This would be a one-time setup thing only. When this is done, user can just run the program anytime.

Run this program:
```
py find_device.py
```
Sample output:
```
================ AVAILABLE AUDIO DEVICES ================
Index [0]: Microsoft Sound Mapper - Input (Channels: 2)
Index [1]: Internal Microphone (Cirrus Log (Channels: 2)
Index [2]: CABLE Output (VB-Audio Virtual  (Channels: 16)
=========================================================

👉 Copy the Index number of your microphone or VB-Cable into config.toml
```
In my case, since the ```CABLE Output (VB-Audio Virtual``` was found in index [2], I will use that index for my ```input_device_index``` variable found in ```config.toml```.

Sample configuration in ```config.toml```
```
[audio]
input_device_index = 2 <--- insert the value here
sample_rate = 16000     
channels = 1            
silence_duration = 5
```

### Note: ### You should check other variables inside config.toml and insert necessary data.

### 3. Set Up a Isolated Virtual Environment (venv)
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

### 4. Install python dependencies
```bash
pip install -r requirements.txt
```

### 5. Initialize Playwright Web Drivers
```bash
playwright install
```

How to Run the App
Ensure your terminal is open in the project folder and your environment is active: (venv).
Launch the tracking application engine:
```Bash
py main.py
```
The Single Sign-On (SSO) Step: A Google Chrome browser window will automatically launch.

Complete your standard Single Sign-On steps inside the browser.

Navigate into your designated workspace room and ensure a fresh, completely blank assistant chat window is open.

Click the + sign in the chat and select Insert Assistant & Agent. Then select **RIE**.

Return to your terminal, press [ENTER], and the system console will attach seamlessly!

Now let the program receive audio and do its job.
