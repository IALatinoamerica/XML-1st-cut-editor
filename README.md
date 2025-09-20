# XML 1st Cut Editor

This project provides a desktop utility that trims Premiere Pro XML timelines by
removing silent sections according to a configurable threshold. The
application analyses only the audio from the first track (A1) and applies the
resulting cuts to every video track in the sequence. The processed timeline is
saved as a new XML file that can be re-imported into Adobe Premiere Pro.

## Features

- PyQt6 graphical interface with controls for silence threshold and minimum
  silence duration.
- Audio analysis using the media referenced in the XML file to locate the
  non-silent sections on track A1.
- Automatic cutting of all video tracks to match the detected speaking
  segments, producing multiple shorter clips instead of a single long clip.
- Logging panel displaying progress while the XML is being processed.
- Batch scripts for setting up the virtual environment and launching the
  application on Windows.

## Requirements

- Python 3.9 or later.
- FFmpeg installed and available on your system `PATH` (required by
  [pydub](https://github.com/jiaaro/pydub) to decode audio from the original
  media files).

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

On Windows you can use the provided batch scripts:

- `setup_env.bat` – creates a virtual environment and installs the
  dependencies listed in `requirements.txt`.
- `run_app.bat` – activates the virtual environment and starts the graphical
  application.

## Usage

1. Export your Premiere Pro sequence as an XML file.
2. Launch the application (`python -m app.main` or `run_app.bat`).
3. Select the exported XML file as the input.
4. Choose an output path for the processed XML file. By default a file with the
   suffix `_cut.xml` is suggested next to the original file.
5. Adjust the silence threshold (in dBFS) and the minimum silence duration if
   needed.
6. Click **Process** and wait for the log to report completion.
7. Import the generated XML back into Premiere Pro.

The XML processor will load the audio referenced by the first audio track in
order to determine which parts of the timeline contain dialogue. Those
intervals are preserved while the rest of the sequence is trimmed away.
