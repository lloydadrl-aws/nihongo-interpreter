# Japanese Meeting STT & Translation Assistant

An automated, real-time tool designed to capture Japanese audio, decode speech-to-text live via microphone/virtual audio routing, and securely stream live structural translations to your local terminal using a browser automation layer.

---

## Prerequisites

Before installing the application, ensure your machine has the following system dependencies installed:

1. **Python 3.11+**: Ensure Python is added to your system environment `PATH` during installation.
2. **Google Chrome**: The browser tool hooks natively into your standard Google Chrome installation path.
3. **Audio Hardware Input**: A working microphone, or a virtual audio cable (like VB-Cable) if routing audio directly from a web meeting (Teams, Zoom, etc.).

---

## Quick Start Installation

Have your team members follow these exact steps to deploy the application on their local device:

### 1. Clone the Repository
```bash
git clone https://github.com/lloydadrl-aws/nihongo-interpreter
cd jp_meeting_assistant
```

### 2. Audio Routing via VB-CABLE (Crucial for Virtual Meetings)

If you are translating audio from a live online meeting (Teams, Zoom, Webex, or a browser window) rather than using a physical microphone in the room, follow these steps:

1. **Install VB-CABLE:** Download and install the driver from [VB-Audio](https://vb-audio.com/Cable/). *Note: A system restart is usually required after installation.*
2. **Configure your Meeting App:** Open your meeting software (e.g., Zoom, Teams) or system sound settings, and change the **Speaker/Output Device** to **CABLE Input (VB-Audio Virtual Cable)**.
3. **Configure the App Script:** Run `python find_devices.py`. Look for **CABLE Output (VB-Audio Virtual Cable)** in the list, note its index number, and put that number into your `config.toml` as shown below.

Now, any audio played in your meeting will drop straight into Rie-san's translator pipeline seamlessly!
