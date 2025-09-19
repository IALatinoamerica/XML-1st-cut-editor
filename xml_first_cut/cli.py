"""Command line interface for the XML first cut editor."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, Optional

from .audio_analysis import SilenceDetectionSettings
from .timeline import (
    compute_preserved_segments,
    rebuild_sequence_tracks,
    update_sequence_metadata,
)
from .xml_parser import load_sequence, write_sequence


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:  # pragma: no cover - argparse feedback
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_xml", type=Path, help="Path to the input Premiere XML file")
    parser.add_argument("output_xml", type=Path, help="Destination path for the processed XML file")
    parser.add_argument(
        "--silence-threshold",
        type=_positive_float,
        default=0.02,
        help="RMS threshold (0-1) that separates silence from signal (default: 0.02)",
    )
    parser.add_argument(
        "--min-silence",
        type=_positive_float,
        default=0.35,
        help="Minimum silence duration in seconds before creating a cut (default: 0.35)",
    )
    parser.add_argument(
        "--min-clip",
        type=_positive_float,
        default=0.5,
        help="Minimum non-silent clip duration in seconds to keep (default: 0.5)",
    )
    parser.add_argument(
        "--padding",
        type=_positive_float,
        default=0.08,
        help="Extra seconds kept before and after each detected segment (default: 0.08)",
    )
    parser.add_argument(
        "--frame-window",
        type=_positive_float,
        default=0.02,
        help="Analysis window size in seconds for RMS measurements (default: 0.02)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity level (default: INFO)",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )


def run_from_args(args: argparse.Namespace) -> int:
    configure_logging(args.log_level)

    if not args.input_xml.exists():
        logging.error("Input XML '%s' does not exist", args.input_xml)
        return 1

    sequence = load_sequence(args.input_xml)
    if not sequence.audio_tracks:
        logging.error("The sequence does not contain any audio tracks")
        return 1

    settings = SilenceDetectionSettings(
        silence_threshold=args.silence_threshold,
        min_silence=args.min_silence,
        min_clip=args.min_clip,
        padding=args.padding,
        frame_window=args.frame_window,
    )

    logging.info("Analyzing first audio track (track %s)", sequence.audio_tracks[0].index)
    segments = compute_preserved_segments(sequence.audio_tracks[0], sequence.fps, settings)

    if not segments:
        logging.warning("No non-silent audio segments detected; the output timeline will be empty")

    total_duration = rebuild_sequence_tracks(sequence, segments)
    update_sequence_metadata(sequence, total_duration)

    output_path = args.output_xml
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_sequence(sequence, output_path)

    logging.info("Wrote processed XML to %s", output_path)
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_from_args(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
