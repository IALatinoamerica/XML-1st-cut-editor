import copy
import math
import os
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, unquote

import xml.etree.ElementTree as ET

from pydub import AudioSegment, silence


LogFunc = Callable[[str], None]


@dataclass
class ClipInfo:
    element: ET.Element
    start: int
    end: int
    in_frame: int
    out_frame: int
    file_path: Optional[str]
    clip_id: str


class XMLProcessingError(Exception):
    """Raised when the XML file cannot be processed."""


def process_xml(
    input_path: str,
    output_path: str,
    min_silence_ms: int,
    silence_threshold_db: int,
    log: Optional[LogFunc] = None,
) -> None:
    """Process the XML file and write the edited version to ``output_path``.

    Parameters
    ----------
    input_path:
        Path to the original XML file exported from Adobe Premiere Pro.
    output_path:
        Destination path where the processed XML file will be stored.
    min_silence_ms:
        Minimum duration (in milliseconds) that must be considered silence
        before a cut is introduced.
    silence_threshold_db:
        Amplitude threshold in dBFS considered as silence. Anything below this
        level is treated as silence. Typical values range between -60 and -30.
    log:
        Optional callable used to report progress information back to the
        caller (usually the GUI).
    """

    def _log(message: str) -> None:
        if log:
            log(message)

    if not os.path.isfile(input_path):
        raise XMLProcessingError(f"Input XML file not found: {input_path}")

    _log("Parsing XML file...")
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as exc:
        raise XMLProcessingError(f"Unable to parse XML file: {exc}") from exc

    root = tree.getroot()

    sequence = root.find('.//sequence')
    if sequence is None:
        raise XMLProcessingError("No <sequence> element was found in the XML file.")

    fps = _resolve_timebase(sequence)
    _log(f"Detected sequence timebase: {fps:.3f} fps")

    audio_track = _get_first_audio_track(sequence)
    if audio_track is None:
        raise XMLProcessingError("Could not locate the first audio track (A1) in the XML file.")

    audio_clips = _extract_clip_items(audio_track, fps, require_media=True)
    if not audio_clips:
        raise XMLProcessingError("The first audio track does not contain any clip items to analyse.")

    audio_cache: Dict[str, AudioSegment] = {}

    non_silent_intervals: List[Tuple[int, int]] = []

    for clip in audio_clips:
        if not clip.file_path:
            _log(f"Skipping audio clip '{clip.clip_id}' without a valid media path.")
            continue

        audio = _load_audio_segment(clip.file_path, audio_cache, _log)
        if audio is None:
            _log(f"Skipping clip '{clip.clip_id}' because its audio could not be loaded.")
            continue

        clip_audio = _slice_clip_audio(audio, clip, fps)
        if clip_audio.duration_seconds <= 0:
            continue

        _log(
            "Detecting non-silent ranges for clip "
            f"'{os.path.basename(clip.file_path)}' (timeline {clip.start}-{clip.end} frames)..."
        )

        detected = silence.detect_nonsilent(
            clip_audio,
            min_silence_len=max(1, min_silence_ms),
            silence_thresh=silence_threshold_db,
        )

        for start_ms, end_ms in detected:
            start_frame = clip.start + _milliseconds_to_frames(start_ms, fps)
            end_frame = clip.start + _milliseconds_to_frames(end_ms, fps)
            end_frame = min(end_frame, clip.end)
            if end_frame > start_frame:
                non_silent_intervals.append((start_frame, end_frame))

    if not non_silent_intervals:
        _log("No non-silent regions detected. The resulting XML will contain an empty timeline.")

    non_silent_intervals = _merge_intervals(sorted(non_silent_intervals), gap_tolerance=1)

    _log(f"Detected {len(non_silent_intervals)} non-silent region(s) across the sequence.")

    _apply_cuts_to_tracks(sequence, non_silent_intervals, fps, _log)

    _update_sequence_duration(sequence, non_silent_intervals)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    _log(f"Processing completed. Output written to: {output_path}")


def _resolve_timebase(sequence: ET.Element) -> float:
    rate = sequence.find('rate')
    timebase_text: Optional[str] = None
    if rate is not None:
        timebase_text = rate.findtext('timebase')
    if not timebase_text:
        # Try legacy location
        timebase_text = sequence.findtext('./media/video/format/samplecharacteristics/rate/timebase')

    if not timebase_text:
        return 30.0

    try:
        timebase = float(timebase_text)
    except ValueError:
        return 30.0

    ntsc_text = None
    if rate is not None:
        ntsc_text = rate.findtext('ntsc')

    if ntsc_text and ntsc_text.strip().upper() == 'TRUE' and timebase in (24, 30, 60):
        # Handle drop-frame NTSC rates
        if math.isclose(timebase, 24):
            return 24000 / 1001
        if math.isclose(timebase, 30):
            return 30000 / 1001
        if math.isclose(timebase, 60):
            return 60000 / 1001

    return timebase


def _get_first_audio_track(sequence: ET.Element) -> Optional[ET.Element]:
    audio_media = sequence.find('./media/audio')
    if audio_media is None:
        return None
    for child in audio_media:
        if child.tag == 'track':
            return child
    return None


def _extract_clip_items(track: ET.Element, fps: float, require_media: bool = False) -> List[ClipInfo]:
    clips: List[ClipInfo] = []
    for clip_elem in track.findall('clipitem'):
        clip_info = _parse_clip_item(clip_elem, fps)
        if clip_info is None:
            continue
        if require_media and not clip_info.file_path:
            continue
        clips.append(clip_info)
    clips.sort(key=lambda c: c.start)
    return clips


def _parse_clip_item(clip_elem: ET.Element, fps: float) -> Optional[ClipInfo]:
    start = _parse_frame_value(clip_elem.findtext('start'))
    end = _parse_frame_value(clip_elem.findtext('end'))
    if end <= start:
        return None

    in_frame = _parse_frame_value(clip_elem.findtext('in'), fallback=0)
    out_frame_text = clip_elem.findtext('out')
    if out_frame_text is not None and out_frame_text.strip() != '':
        out_frame = _parse_frame_value(out_frame_text)
    else:
        out_frame = in_frame + (end - start)

    file_path = _extract_media_path(clip_elem)
    clip_id = clip_elem.get('id', 'clip')

    return ClipInfo(
        element=clip_elem,
        start=start,
        end=end,
        in_frame=in_frame,
        out_frame=out_frame,
        file_path=file_path,
        clip_id=clip_id,
    )


def _extract_media_path(clip_elem: ET.Element) -> Optional[str]:
    file_elem = clip_elem.find('file')
    if file_elem is None:
        return None
    pathurl = file_elem.findtext('pathurl')
    if not pathurl:
        return None
    return _pathurl_to_path(pathurl)


def _pathurl_to_path(pathurl: str) -> str:
    if pathurl.startswith('file://'):
        parsed = urlparse(pathurl)
        path = unquote(parsed.path)
        if os.name == 'nt' and path.startswith('/') and parsed.netloc:
            # Windows paths may include drive letter in netloc
            return f"{parsed.netloc}:{path}"
        if os.name == 'nt' and path.startswith('/') and len(path) > 2 and path[2] == ':':
            return path[1:]
        return path
    return pathurl


def _load_audio_segment(
    file_path: str,
    cache: Dict[str, AudioSegment],
    log: LogFunc,
) -> Optional[AudioSegment]:
    resolved_path = os.path.abspath(file_path)
    if resolved_path in cache:
        return cache[resolved_path]

    if not os.path.exists(resolved_path):
        log(f"Audio file not found on disk: {resolved_path}")
        return None

    try:
        log(f"Loading audio from: {resolved_path}")
        audio = AudioSegment.from_file(resolved_path)
    except Exception as exc:  # pylint: disable=broad-except
        log(f"Failed to load audio '{resolved_path}': {exc}")
        return None

    cache[resolved_path] = audio
    return audio


def _slice_clip_audio(audio: AudioSegment, clip: ClipInfo, fps: float) -> AudioSegment:
    start_ms = _frames_to_milliseconds(clip.in_frame, fps)
    end_ms = _frames_to_milliseconds(clip.out_frame, fps)
    start_ms = max(0, start_ms)
    end_ms = max(start_ms, end_ms)
    return audio[start_ms:end_ms]


def _merge_intervals(
    intervals: Iterable[Tuple[int, int]],
    gap_tolerance: int = 0,
) -> List[Tuple[int, int]]:
    merged: List[Tuple[int, int]] = []
    for start, end in intervals:
        if end <= start:
            continue
        if not merged:
            merged.append((start, end))
            continue
        last_start, last_end = merged[-1]
        if start <= last_end + gap_tolerance:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _apply_cuts_to_tracks(
    sequence: ET.Element,
    intervals: List[Tuple[int, int]],
    fps: float,
    log: LogFunc,
) -> None:
    if not intervals:
        log("Removing all clip items because no non-silent regions were found.")

    clip_counts: Dict[str, int] = {}

    video_parent = sequence.find('./media/video')
    if video_parent is not None:
        for index, track in enumerate(list(video_parent)):
            if track.tag != 'track':
                continue
            new_track = _rebuild_track(track, intervals, clip_counts, fps)
            video_parent.remove(track)
            video_parent.insert(index, new_track)

    audio_parent = sequence.find('./media/audio')
    if audio_parent is not None:
        first_track_processed = False
        for index, track in enumerate(list(audio_parent)):
            if track.tag != 'track':
                continue
            if not first_track_processed:
                new_track = _rebuild_track(track, intervals, clip_counts, fps)
                audio_parent.remove(track)
                audio_parent.insert(index, new_track)
                first_track_processed = True
            else:
                # Leave the remaining audio tracks untouched
                continue


def _rebuild_track(
    track: ET.Element,
    intervals: List[Tuple[int, int]],
    clip_counts: Dict[str, int],
    fps: float,
) -> ET.Element:
    new_track = ET.Element('track', track.attrib)

    # Preserve any non-clip items at the beginning of the track
    for child in track:
        if child.tag != 'clipitem':
            new_track.append(copy.deepcopy(child))

    for clip_elem in track.findall('clipitem'):
        clip_info = _parse_clip_item(clip_elem, fps)
        if clip_info is None:
            continue

        clip_length = clip_info.end - clip_info.start
        if clip_length <= 0:
            continue

        for interval_start, interval_end in intervals:
            overlap_start = max(clip_info.start, interval_start)
            overlap_end = min(clip_info.end, interval_end)
            if overlap_end - overlap_start <= 0:
                continue

            new_clip = copy.deepcopy(clip_elem)
            clip_counts.setdefault(clip_info.clip_id, 0)
            clip_counts[clip_info.clip_id] += 1
            new_id = f"{clip_info.clip_id}_seg{clip_counts[clip_info.clip_id]}"
            new_clip.set('id', new_id)

            _set_or_create_text(new_clip, 'start', str(overlap_start))
            _set_or_create_text(new_clip, 'end', str(overlap_end))

            relative_offset = overlap_start - clip_info.start
            new_in = clip_info.in_frame + relative_offset
            new_out = new_in + (overlap_end - overlap_start)
            _set_or_create_text(new_clip, 'in', str(new_in))
            _set_or_create_text(new_clip, 'out', str(new_out))

            duration_elem = new_clip.find('duration')
            if duration_elem is not None:
                duration_elem.text = str(overlap_end - overlap_start)

            # Remove link information to avoid mismatched clip references
            for link_elem in list(new_clip.findall('link')):
                new_clip.remove(link_elem)

            new_track.append(new_clip)

    return new_track


def _set_or_create_text(element: ET.Element, tag: str, text: str) -> None:
    child = element.find(tag)
    if child is None:
        child = ET.SubElement(element, tag)
    child.text = text


def _update_sequence_duration(sequence: ET.Element, intervals: List[Tuple[int, int]]) -> None:
    if not intervals:
        new_end = 0
    else:
        new_end = intervals[-1][1]

    for tag in ('out', 'end', 'duration'):
        elem = sequence.find(tag)
        if elem is not None:
            elem.text = str(new_end)


def _parse_frame_value(value: Optional[str], fallback: int = 0) -> int:
    if value is None or value.strip() == '':
        return fallback
    try:
        return int(round(float(value)))
    except ValueError:
        return fallback


def _frames_to_milliseconds(frames: int, fps: float) -> int:
    return int(round(frames * 1000 / fps))


def _milliseconds_to_frames(milliseconds: int, fps: float) -> int:
    return int(round(milliseconds * fps / 1000))
