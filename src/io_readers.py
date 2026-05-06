"""Directory walking and JSON parsing."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .metadata import (
    expected_phase_dir,
    parse_event,
    parse_json_filename,
    parse_json_filename_any,
    parse_serial_folder,
    phase_label,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Record:
    event: str
    serial: str
    phase: str
    position: str
    repeat_index: int
    path: Path
    data: dict


def _iter_json_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.json"):
        if path.is_file():
            yield path


def load_records(root: Path) -> List[Record]:
    event = parse_event(root)
    if not event:
        raise ValueError(
            f"Root folder name must be 'Imatest_data_<EVENT>', got '{root.name}'."
        )

    records: List[Record] = []
    for phase_dir in ["init", "after_test"]:
        phase_path = root / phase_dir
        if not phase_path.exists():
            logger.warning("Missing phase folder: %s", phase_path)
            continue

        label = phase_label(phase_dir)
        if not label:
            logger.warning("Unknown phase folder: %s", phase_path)
            continue

        for serial_folder in phase_path.iterdir():
            if not serial_folder.is_dir():
                continue
            folder_meta = parse_serial_folder(serial_folder, event, phase_dir)
            if not folder_meta:
                logger.warning("Skipping non-matching folder: %s", serial_folder)
                continue

            result_dir = serial_folder / "result"
            if not result_dir.exists():
                alt_dir = serial_folder / "Results"
                if alt_dir.exists():
                    result_dir = alt_dir
                else:
                    logger.warning("Missing result folder: %s", result_dir)
                    continue

            for json_path in result_dir.glob("*.json"):
                file_meta = parse_json_filename(json_path.name, event)
                if not file_meta:
                    logger.warning("Skipping non-matching file: %s", json_path)
                    continue
                if file_meta.serial != folder_meta.serial:
                    logger.warning(
                        "Serial mismatch between folder and file: %s", json_path
                    )
                    continue

                try:
                    with json_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as exc:  # pragma: no cover - resilient parsing
                    logger.warning("Failed to read %s: %s", json_path, exc)
                    continue

                records.append(
                    Record(
                        event=event,
                        serial=file_meta.serial,
                        phase=label,
                        position=file_meta.position,
                        repeat_index=file_meta.repeat_index,
                        path=json_path,
                        data=data,
                    )
                )

    if not records:
        logger.warning("No valid JSON records found under %s", root)
    return records


def _infer_phase_from_path(path: Path) -> Optional[str]:
    for part in path.parts:
        if part == "init":
            return "Before"
        if part == "after_test":
            return "After"
    return None


def _find_event_root(path: Path) -> Optional[Path]:
    for parent in path.parents:
        event = parse_event(parent)
        if event:
            return parent
    return None


def load_records_from_files(files: List[Path]) -> List[Record]:
    records: List[Record] = []
    for json_path in files:
        if not json_path.is_file():
            continue

        meta = parse_json_filename_any(json_path.name)
        if not meta:
            logger.warning("Skipping non-matching file: %s", json_path)
            continue

        event = meta.event
        event_root = _find_event_root(json_path)
        if event_root:
            event = parse_event(event_root) or event

        phase = _infer_phase_from_path(json_path)
        if not phase:
            logger.warning("Unable to infer phase for file: %s", json_path)
            continue

        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to read %s: %s", json_path, exc)
            continue

        records.append(
            Record(
                event=event,
                serial=meta.serial,
                phase=phase,
                position=meta.position,
                repeat_index=meta.repeat_index,
                path=json_path,
                data=data,
            )
        )

    if not records:
        logger.warning("No valid JSON records found in selected files")
    return records


def load_records_from_files_for_phase(files: List[Path], phase: str) -> List[Record]:
    records: List[Record] = []
    for json_path in files:
        if not json_path.is_file():
            continue

        meta = parse_json_filename_any(json_path.name)
        if not meta:
            logger.warning("Skipping non-matching file: %s", json_path)
            continue

        event = meta.event
        event_root = _find_event_root(json_path)
        if event_root:
            event = parse_event(event_root) or event

        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to read %s: %s", json_path, exc)
            continue

        records.append(
            Record(
                event=event,
                serial=meta.serial,
                phase=phase,
                position=meta.position,
                repeat_index=meta.repeat_index,
                path=json_path,
                data=data,
            )
        )

    if not records:
        logger.warning("No valid JSON records found in selected files")
    return records


def load_records_from_phase_root(root: Path, phase: str) -> List[Record]:
    if root.is_file():
        return load_records_from_files_for_phase([root], phase)

    scan_root = root
    event = parse_event(root)

    expected_dir = expected_phase_dir(phase)
    if event and expected_dir:
        candidate = root / expected_dir
        if candidate.exists():
            scan_root = candidate

    if not event:
        event_root = _find_event_root(root)
        if event_root:
            event = parse_event(event_root)

    records: List[Record] = []
    for json_path in scan_root.rglob("*.json"):
        if not json_path.is_file():
            continue

        if event:
            meta = parse_json_filename(json_path.name, event)
        else:
            meta = parse_json_filename_any(json_path.name)

        if not meta:
            logger.warning("Skipping non-matching file: %s", json_path)
            continue

        event_value = event or meta.event

        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.warning("Failed to read %s: %s", json_path, exc)
            continue

        records.append(
            Record(
                event=event_value,
                serial=meta.serial,
                phase=phase,
                position=meta.position,
                repeat_index=meta.repeat_index,
                path=json_path,
                data=data,
            )
        )

    if not records:
        logger.warning("No valid JSON records found under %s", scan_root)
    return records
