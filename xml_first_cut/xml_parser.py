"""Utilities for parsing and manipulating Premiere Pro XML files."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional
import logging
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse


LOGGER = logging.getLogger(__name__)


@dataclass
class ClipItemData:
    """Representation of a clip item inside a track."""

    id: str
    name: str
    start: int
    end: int
    in_frame: int
    out_frame: int
    duration: int
    file_id: Optional[str]
    file_path: Optional[str]
    element: ET.Element


@dataclass
class TrackData:
    """Representation of a single track."""

    kind: str  # "video" or "audio"
    index: int
    element: ET.Element
    clipitems: List[ClipItemData] = field(default_factory=list)


@dataclass
class SequenceData:
    """All the information required to rebuild a sequence."""

    tree: ET.ElementTree
    root: ET.Element
    element: ET.Element
    fps: Fraction
    video_tracks: List[TrackData]
    audio_tracks: List[TrackData]


def _parse_fractional_rate(rate_element: Optional[ET.Element]) -> Fraction:
    """Parse the timebase information from a `<rate>` element."""
    if rate_element is None:
        return Fraction(25, 1)

    timebase_text = rate_element.findtext("timebase", default="25")
    ntsc_text = rate_element.findtext("ntsc", default="FALSE").strip().upper()

    try:
        timebase = int(timebase_text)
    except ValueError:
        timebase = int(float(timebase_text))

    if ntsc_text == "TRUE":
        # Drop-frame style frame rate.
        return Fraction(timebase * 1000, 1001)
    return Fraction(timebase, 1)


def _text_as_int(element: ET.Element, tag: str, default: int = 0) -> int:
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    try:
        return int(child.text.strip())
    except ValueError:
        return int(float(child.text.strip()))


def _parse_pathurl(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        netloc = parsed.netloc
        path = unquote(parsed.path)
        if netloc and path:
            path = f"/{netloc}{path}"
        if path.startswith("/") and len(path) > 2 and path[1].isalpha() and path[2] == ":":
            # Windows drive letter
            path = path[1:]
        return path
    return unquote(value)


def _collect_file_lookup(root: ET.Element) -> Dict[str, ET.Element]:
    lookup: Dict[str, ET.Element] = {}
    for file_elem in root.findall(".//file"):
        file_id = file_elem.get("id")
        if file_id and file_id not in lookup:
            lookup[file_id] = file_elem
    return lookup


def _parse_clipitem(
    clip_elem: ET.Element,
    file_lookup: Dict[str, ET.Element],
) -> ClipItemData:
    clip_id = clip_elem.get("id") or "clip"
    name = clip_elem.findtext("name", default=clip_id)
    start = _text_as_int(clip_elem, "start", default=0)
    end = _text_as_int(clip_elem, "end", default=start)
    in_frame = _text_as_int(clip_elem, "in", default=0)
    out_frame = _text_as_int(clip_elem, "out", default=in_frame + (end - start))
    duration = _text_as_int(clip_elem, "duration", default=end - start)

    file_elem = clip_elem.find("file")
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    if file_elem is not None:
        file_id = file_elem.get("id") or file_elem.get("idref")
        path_text = file_elem.findtext("pathurl")
        if path_text:
            file_path = _parse_pathurl(path_text)
        elif file_id and file_id in file_lookup:
            path_elem = file_lookup[file_id].find("pathurl")
            if path_elem is not None and path_elem.text:
                file_path = _parse_pathurl(path_elem.text)

    if file_path:
        file_path = str(Path(file_path))

    return ClipItemData(
        id=clip_id,
        name=name,
        start=start,
        end=end,
        in_frame=in_frame,
        out_frame=out_frame,
        duration=duration,
        file_id=file_id,
        file_path=file_path,
        element=clip_elem,
    )


def _parse_track(
    track_elem: ET.Element,
    kind: str,
    index: int,
    file_lookup: Dict[str, ET.Element],
) -> TrackData:
    clipitems: List[ClipItemData] = []
    for clip_elem in track_elem.findall("clipitem"):
        clipitems.append(_parse_clipitem(clip_elem, file_lookup))
    clipitems.sort(key=lambda item: item.start)
    return TrackData(kind=kind, index=index, element=track_elem, clipitems=clipitems)


def load_sequence(xml_path: str | Path) -> SequenceData:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    sequence_elem = root.find("sequence")
    if sequence_elem is None:
        sequence_elem = root.find(".//sequence")
    if sequence_elem is None:
        raise ValueError("No <sequence> element found in XML")

    fps = _parse_fractional_rate(sequence_elem.find("rate"))
    file_lookup = _collect_file_lookup(root)

    video_tracks: List[TrackData] = []
    audio_tracks: List[TrackData] = []

    media_elem = sequence_elem.find("media")
    if media_elem is not None:
        video_elem = media_elem.find("video")
        if video_elem is not None:
            for idx, track_elem in enumerate(video_elem.findall("track"), start=1):
                video_tracks.append(_parse_track(track_elem, "video", idx, file_lookup))
        audio_elem = media_elem.find("audio")
        if audio_elem is not None:
            for idx, track_elem in enumerate(audio_elem.findall("track"), start=1):
                audio_tracks.append(_parse_track(track_elem, "audio", idx, file_lookup))

    return SequenceData(
        tree=tree,
        root=root,
        element=sequence_elem,
        fps=fps,
        video_tracks=video_tracks,
        audio_tracks=audio_tracks,
    )


def write_sequence(sequence: SequenceData, output_path: str | Path) -> None:
    sequence.tree.write(output_path, encoding="utf-8", xml_declaration=True)


__all__ = [
    "ClipItemData",
    "TrackData",
    "SequenceData",
    "load_sequence",
    "write_sequence",
]
