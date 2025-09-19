"""Audio analysis utilities to detect non-silent sections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import logging

import numpy as np
from moviepy.audio.io.AudioFileClip import AudioFileClip


LOGGER = logging.getLogger(__name__)


@dataclass
class SilenceDetectionSettings:
    """Parameters that control the silence detection behaviour."""

    silence_threshold: float = 0.02
    min_silence: float = 0.35
    min_clip: float = 0.5
    padding: float = 0.08
    frame_window: float = 0.02
    sample_rate: int = 44_100


def _to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert the audio to a mono numpy array."""
    if audio.ndim == 1:
        return audio.astype(np.float64)
    return audio.mean(axis=1).astype(np.float64)


def _detect_segments(
    mono_audio: np.ndarray,
    sample_rate: int,
    settings: SilenceDetectionSettings,
) -> List[Tuple[float, float]]:
    """Detect non-silent segments within the provided mono audio array."""
    if mono_audio.size == 0:
        return []

    window_samples = max(1, int(sample_rate * settings.frame_window))
    total_duration = mono_audio.size / sample_rate
    rms_values: List[float] = []

    for start in range(0, mono_audio.size, window_samples):
        end = min(start + window_samples, mono_audio.size)
        window = mono_audio[start:end]
        if window.size == 0:
            break
        rms = float(np.sqrt(np.mean(np.square(window))))
        rms_values.append(rms)

    frame_duration = settings.frame_window
    non_silent_segments: List[Tuple[float, float]] = []

    current_start: float | None = None
    last_loud_time: float | None = None
    accumulated_silence = 0.0

    for index, rms in enumerate(rms_values):
        frame_start = index * frame_duration
        frame_end = min(frame_start + frame_duration, total_duration)
        is_loud = rms >= settings.silence_threshold

        if is_loud:
            if current_start is None:
                current_start = frame_start
            last_loud_time = frame_end
            accumulated_silence = 0.0
        else:
            if current_start is not None:
                accumulated_silence += frame_end - frame_start
                if accumulated_silence >= settings.min_silence:
                    end_time = last_loud_time if last_loud_time is not None else frame_start
                    if end_time > current_start:
                        non_silent_segments.append((current_start, end_time))
                    current_start = None
                    last_loud_time = None
                    accumulated_silence = 0.0

    if current_start is not None:
        end_time = last_loud_time if last_loud_time is not None else total_duration
        if end_time > current_start:
            non_silent_segments.append((current_start, end_time))

    # Apply padding and drop short segments.
    padded_segments: List[Tuple[float, float]] = []
    for start, end in non_silent_segments:
        duration = end - start
        if duration < settings.min_clip:
            continue
        padded_start = max(0.0, start - settings.padding)
        padded_end = min(total_duration, end + settings.padding)
        padded_segments.append((padded_start, padded_end))

    if not padded_segments:
        return []

    # Merge overlapping padded segments.
    padded_segments.sort(key=lambda s: s[0])
    merged: List[Tuple[float, float]] = [padded_segments[0]]
    for start, end in padded_segments[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def detect_non_silent_sections(
    file_path: str,
    start_seconds: float,
    end_seconds: float,
    settings: SilenceDetectionSettings,
) -> List[Tuple[float, float]]:
    """Return a list of non-silent segments relative to the requested interval.

    The segments are expressed relative to ``start_seconds``. When the requested
    interval exceeds the file boundaries, it is clamped to the available audio
    duration. The returned list contains tuples of ``(start, end)`` times in
    seconds.
    """
    if end_seconds <= start_seconds:
        return []

    try:
        clip = AudioFileClip(file_path)
    except OSError as exc:  # pragma: no cover - propagated for the CLI to display
        LOGGER.error("Unable to open audio for '%s': %s", file_path, exc)
        raise

    try:
        media_duration = clip.duration if clip.duration is not None else end_seconds
        actual_start = max(0.0, min(start_seconds, media_duration))
        actual_end = max(actual_start, min(end_seconds, media_duration))
        if actual_end <= actual_start:
            return []

        subclip = clip.subclip(actual_start, actual_end)
        try:
            audio_array = subclip.to_soundarray(fps=settings.sample_rate)
        finally:
            subclip.close()
    finally:
        clip.close()

    mono = _to_mono(audio_array)
    detected = _detect_segments(mono, settings.sample_rate, settings)

    if not detected:
        return []

    offset = actual_start - start_seconds
    adjusted: List[Tuple[float, float]] = []
    for seg_start, seg_end in detected:
        adj_start = max(0.0, seg_start - offset)
        adj_end = max(0.0, seg_end - offset)
        if adj_end > adj_start:
            adjusted.append((adj_start, adj_end))

    return adjusted


__all__ = [
    "SilenceDetectionSettings",
    "detect_non_silent_sections",
]
