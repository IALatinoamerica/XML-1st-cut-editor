"""Timeline processing to apply non-silent segments to all tracks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import copy
import logging

from fractions import Fraction
import xml.etree.ElementTree as ET

from .audio_analysis import SilenceDetectionSettings, detect_non_silent_sections
from .xml_parser import ClipItemData, SequenceData, TrackData


LOGGER = logging.getLogger(__name__)


@dataclass
class TimelineSegment:
    """A portion of the original timeline that should be preserved."""

    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start


@dataclass
class SegmentMapping:
    """Maps a preserved segment to its position in the output timeline."""

    source_start: int
    source_end: int
    output_start: int
    output_end: int


def _frames_to_seconds(frames: int, fps: Fraction) -> float:
    return float(frames / fps)


def _seconds_to_frames(seconds: float, fps: Fraction) -> int:
    return max(0, int(round(seconds * float(fps))))


def _merge_segments(segments: List[TimelineSegment]) -> List[TimelineSegment]:
    if not segments:
        return []
    segments.sort(key=lambda seg: seg.start)
    merged: List[TimelineSegment] = [segments[0]]
    for segment in segments[1:]:
        last = merged[-1]
        if segment.start <= last.end + 1:
            last.end = max(last.end, segment.end)
        else:
            merged.append(TimelineSegment(segment.start, segment.end))
    return merged


def _segment_mappings(segments: List[TimelineSegment]) -> List[SegmentMapping]:
    mappings: List[SegmentMapping] = []
    current_output = 0
    for segment in segments:
        if segment.duration <= 0:
            continue
        mappings.append(
            SegmentMapping(
                source_start=segment.start,
                source_end=segment.end,
                output_start=current_output,
                output_end=current_output + segment.duration,
            )
        )
        current_output += segment.duration
    return mappings


def _set_child_text(element: ET.Element, tag: str, value: str) -> None:
    child = element.find(tag)
    if child is None:
        child = ET.SubElement(element, tag)
    child.text = value


def _clone_clipitem(
    clip: ClipItemData,
    new_start: int,
    new_end: int,
    new_in: int,
    new_out: int,
    id_counters: Dict[str, int],
) -> ET.Element:
    element = copy.deepcopy(clip.element)
    duration = max(0, new_end - new_start)
    counter = id_counters.get(clip.id, 0) + 1
    id_counters[clip.id] = counter
    element.set("id", f"{clip.id}_cut{counter}")

    _set_child_text(element, "start", str(new_start))
    _set_child_text(element, "end", str(new_end))
    _set_child_text(element, "in", str(new_in))
    _set_child_text(element, "out", str(new_out))
    _set_child_text(element, "duration", str(duration))

    for link in list(element.findall("link")):
        element.remove(link)

    return element


def _build_track(
    track: TrackData,
    mappings: List[SegmentMapping],
) -> ET.Element:
    new_track = copy.deepcopy(track.element)
    for clip_elem in list(new_track.findall("clipitem")):
        new_track.remove(clip_elem)

    id_counters: Dict[str, int] = {}
    new_clips: List[ET.Element] = []

    for mapping in mappings:
        for clip in track.clipitems:
            if clip.end <= mapping.source_start or clip.start >= mapping.source_end:
                continue
            overlap_start = max(clip.start, mapping.source_start)
            overlap_end = min(clip.end, mapping.source_end)
            if overlap_end <= overlap_start:
                continue

            offset_within_segment = overlap_start - mapping.source_start
            new_start = mapping.output_start + offset_within_segment
            new_end = new_start + (overlap_end - overlap_start)
            new_in = clip.in_frame + (overlap_start - clip.start)
            new_out = new_in + (overlap_end - overlap_start)

            new_clip = _clone_clipitem(clip, new_start, new_end, new_in, new_out, id_counters)
            new_clips.append(new_clip)

    new_clips.sort(key=lambda elem: int(elem.findtext("start", "0")))
    for clip_elem in new_clips:
        new_track.append(clip_elem)

    return new_track


def compute_preserved_segments(
    first_audio_track: TrackData,
    fps: Fraction,
    settings: SilenceDetectionSettings,
) -> List[TimelineSegment]:
    segments: List[TimelineSegment] = []
    for clip in first_audio_track.clipitems:
        if not clip.file_path:
            LOGGER.warning("Skipping clip %s because the file path is missing", clip.id)
            continue
        source_start = _frames_to_seconds(clip.in_frame, fps)
        source_end = _frames_to_seconds(clip.out_frame, fps)
        clip_segments = detect_non_silent_sections(
            clip.file_path,
            source_start,
            source_end,
            settings,
        )
        for seg_start, seg_end in clip_segments:
            timeline_start = clip.start + _seconds_to_frames(seg_start, fps)
            timeline_end = clip.start + _seconds_to_frames(seg_end, fps)
            timeline_start = max(clip.start, min(timeline_start, clip.end))
            timeline_end = max(clip.start, min(timeline_end, clip.end))
            if timeline_end > timeline_start:
                segments.append(TimelineSegment(timeline_start, timeline_end))

    merged = _merge_segments(segments)
    LOGGER.info("Detected %d non-silent segments", len(merged))
    return merged


def rebuild_sequence_tracks(
    sequence: SequenceData,
    segments: List[TimelineSegment],
) -> int:
    mappings = _segment_mappings(segments)
    total_duration = mappings[-1].output_end if mappings else 0

    media_elem = sequence.element.find("media")
    if media_elem is None:
        return total_duration

    video_elem = media_elem.find("video")
    if video_elem is not None:
        for track_elem in list(video_elem.findall("track")):
            video_elem.remove(track_elem)
        for track in sequence.video_tracks:
            video_elem.append(_build_track(track, mappings))

    audio_elem = media_elem.find("audio")
    if audio_elem is not None:
        for track_elem in list(audio_elem.findall("track")):
            audio_elem.remove(track_elem)
        for track in sequence.audio_tracks:
            audio_elem.append(_build_track(track, mappings))

    return total_duration


def update_sequence_metadata(sequence: SequenceData, total_duration: int) -> None:
    _set_child_text(sequence.element, "in", "0")
    _set_child_text(sequence.element, "out", str(total_duration))
    _set_child_text(sequence.element, "duration", str(total_duration))

    timecode = sequence.element.find("timecode")
    if timecode is not None:
        _set_child_text(timecode, "duration", str(total_duration))


__all__ = [
    "TimelineSegment",
    "SegmentMapping",
    "compute_preserved_segments",
    "rebuild_sequence_tracks",
    "update_sequence_metadata",
]
