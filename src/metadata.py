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


def parse_event(root: Path) -> Optional[str]:
    match = EVENT_RE.match(root.name)
    if not match:
        return None
    return match.group("event")


def parse_serial_folder(folder: Path, event: str, phase: str) -> Optional[ParsedFolderMeta]:
    # Accept both with and without VQF12 prefix.
    # Examples:
    # - VQF12_<EVENT>_<SERIAL>_init
    # - <EVENT>_<SERIAL>_init
    phase_suffix = "init" if phase == "init" else "after"
    pattern = rf"^(?:VQF12_)?{re.escape(event)}_(?P<serial>\d+)_{phase_suffix}$"
    match = re.match(pattern, folder.name)
    if not match:
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
    relaxed = rf"^(?:VQF12_)?{re.escape(event)}_(?P<serial>\d+)_(?P<position>.+)_tiff\.json$"
    match = re.match(relaxed, filename)
    if match:
        return ParsedFileMeta(
            event=event,
            serial=match.group("serial"),
            position=match.group("position"),
            repeat_index=1,
        )

    strict = rf"^(?:VQF12_)?{re.escape(event)}_(?P<serial>\d+)_(?P<position>.+?)(?:_(?P<nn>\d+))?\.json$"
    match = re.match(strict, filename)
    if match:
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
