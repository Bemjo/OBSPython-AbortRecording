# Abort Recording

## Description
Abort Recording is a Python script designed to stop the current recording in OBS (Open Broadcaster Software) and send the resulting files to the user's trash bin. It provides a convenient way to discard recordings that are no longer needed.

## Requirements
- Python >= 3.6
- [send2trash](https://pypi.org/project/send2trash/) Python module

## Installation
1. Ensure Python >= 3.6 is installed on your system.
2. Ensure OBS is correctly setup to support python scripts. This is not enabled by default.
3. Install python module send2trash with ```python -m pip install -U send2trash```

## Usage
1. Copy the `Abort_Recording.py` script to a location accessible by OBS.
2. In OBS, go to `Tools` > `Scripts`.
3. Click the `+` icon to add a new script.
4. Browse and select `abort_recording.py`.
5. The script will now appear in the Scripts window.
6. (Optional) Give a name to this hotkey as it would appear in the OBS hotkey settings menu.
7. Assign a hotkey in the OBS settings to the new hotkey (Default: Abort Recording).
8. While recording, press the hotkey assigned previously. Your recording will stop, and ALL files generated during will be sent to your trash bin.

**Note:** This script assumes that OBS is properly configured and running with Python scripting enabled.

## Disclaimer
This script is provided as-is, without any warranties or guarantees. Use it at your own risk. The author is not responsible for any data loss or other issues that may arise from its use.
