"""Metadata parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


EVENT_RE = re.compile(r"^Imatest_data_(?P<event>.+)$")


@dataclass(frozen=True)
class ParsedFileMeta:
    event: str
    serial: str
    position: str
    repeat_index: int


@dataclass(frozen=True)
class ParsedFolderMeta:
    event: str
    serial: str
    phase: str


def _event_matches(expected_event: str, parsed_event: str) -> bool:
    expected = expected_event.strip().lower()
    parsed = parsed_event.strip().lower()
    if not expected or not parsed:
        return False
    if expected == parsed:
        return True
    parsed_tokens = [t for t in re.split(r"[_\-\s]+", parsed) if t]
    if expected in parsed_tokens:
        return True
    return expected in parsed


def parse_event(root: Path) -> Optional[str]:
    match = EVENT_RE.match(root.name)
    if not match:
        return None
    return match.group("event")


def parse_serial_folder(folder: Path, event: str, phase: str) -> Optional[ParsedFolderMeta]:
    # Accept flexible event token in folder names.
    # Examples:
    # - VQF12_<EVENT>_<SERIAL>_init
    # - <EVENT>_<SERIAL>_init
    # - ViOnyx_<EVENT>_<SERIAL>_init
    phase_suffix = "init" if phase == "init" else "after"
    pattern = rf"^(?:VQF12_)?(?P<event>.+)_(?P<serial>\d+)_{phase_suffix}$"
    match = re.match(pattern, folder.name)
    if not match:
        return None
    parsed_event = match.group("event")
    if not _event_matches(event, parsed_event):
        return None
    return ParsedFolderMeta(event=event, serial=match.group("serial"), phase=phase)


def parse_json_filename(filename: str, event: str) -> Optional[ParsedFileMeta]:
    # Accept both with and without VQF12 prefix.
    # Accept optional trailing repeat index <NN>.
    # Examples:
    # - VQF12_<EVENT>_<SERIAL>_<POSITION>_<NN>.json
    # - VQF12_<EVENT>_<SERIAL>_<POSITION>.json
    # - <EVENT>_<SERIAL>_<POSITION>_<NN>.json
    # - <EVENT>_<SERIAL>_<POSITION>.json
    relaxed = r"^(?:VQF12_)?(?P<event>.+)_(?P<serial>\d+)_(?P<position>.+)_tiff\.json$"
    match = re.match(relaxed, filename)
    if match:
        parsed_event = match.group("event")
        if not _event_matches(event, parsed_event):
            return None
        return ParsedFileMeta(
            event=event,
            serial=match.group("serial"),
            position=match.group("position"),
            repeat_index=1,
        )

    strict = r"^(?:VQF12_)?(?P<event>.+)_(?P<serial>\d+)_(?P<position>.+?)(?:_(?P<nn>\d+))?\.json$"
    match = re.match(strict, filename)
    if match:
        parsed_event = match.group("event")
        if not _event_matches(event, parsed_event):
            return None
        nn = match.group("nn")
        return ParsedFileMeta(
            event=event,
            serial=match.group("serial"),
            position=match.group("position"),
            repeat_index=int(nn) if nn is not None else 1,
        )
    return None


def parse_json_filename_any(filename: str) -> Optional[ParsedFileMeta]:
    # Accept both with and without VQF12 prefix and optional trailing <NN>.
    # Relaxed: (VQF12_)?<EVENT>_<SERIAL>_<POSITION>_tiff.json
    relaxed = r"^(?:VQF12_)?(?P<event>.+)_(?P<serial>\d+)_(?P<position>.+)_tiff\.json$"
    match = re.match(relaxed, filename)
    if match:
        return ParsedFileMeta(
            event=match.group("event"),
            serial=match.group("serial"),
            position=match.group("position"),
            repeat_index=1,
        )

    strict = r"^(?:VQF12_)?(?P<event>.+)_(?P<serial>\d+)_(?P<position>.+?)(?:_(?P<nn>\d+))?\.json$"
    match = re.match(strict, filename)
    if match:
        nn = match.group("nn")
        return ParsedFileMeta(
            event=match.group("event"),
            serial=match.group("serial"),
            position=match.group("position"),
            repeat_index=int(nn) if nn is not None else 1,
        )
    return None


def phase_label(phase_dir: str) -> Optional[str]:
    if phase_dir == "init":
        return "Before"
    if phase_dir == "after_test":
        return "After"
    return None


def expected_phase_dir(phase_label_value: str) -> Optional[str]:
    if phase_label_value == "Before":
        return "init"
    if phase_label_value == "After":
        return "after_test"
    return None
