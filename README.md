# XML First Cut Editor

This project provides a command-line application that reads a Final Cut Pro XML file exported from Adobe Premiere Pro, analyzes the first audio track to detect silent regions, and generates a new XML file with those silences removed. The resulting XML reorganizes the timeline into a set of contiguous clips that contain only the detected non-silent portions while cutting all video and audio tracks in sync.

## Features

* Parses Premiere Pro XML sequences and collects file references for every clip.
* Analyzes the first audio track (A1) and detects non-silent sections using waveform RMS measurements.
* Applies the computed cut points to every video and audio track in the sequence.
* Writes a brand new XML sequence where the remaining clips are back-to-back without gaps so further editing can be performed manually.

## Requirements

* Python 3.9+
* FFmpeg available on the system path (required by `moviepy` to read audio from video files).

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m xml_first_cut.cli input.xml output.xml
```

### Optional arguments

* `--silence-threshold` – RMS threshold (0 to 1) used to classify audio frames as silence. Default: `0.02`.
* `--min-silence` – Minimum silence duration (seconds) that must be reached before a cut is created. Default: `0.35`.
* `--min-clip` – Minimum duration (seconds) for a clip to be kept. Default: `0.5`.
* `--padding` – Extra audio (seconds) kept at the start and end of each detected segment. Default: `0.08`.
* `--frame-window` – Analysis window (seconds) for RMS computation. Default: `0.02`.

## Batch helpers

Two Windows batch files are provided for convenience:

* `setup_env.bat` – Creates a virtual environment in `.venv` and installs dependencies from `requirements.txt`.
* `run_app.bat` – Activates the virtual environment and runs the main application. Edit the script or pass arguments manually to point to your source and destination XML files.

## Limitations

* Only the first audio track is used to calculate cut points.
* The script expects an XML structure compatible with Premiere Pro / Final Cut Pro 7 XML exports.
* `<link>` elements between clip items are removed in the generated XML to avoid invalid references.
* FFmpeg must be installed separately (moviepy relies on it to read audio).

