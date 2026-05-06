"""CLI entry for Imatest SFRreg batch analysis."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.runner import run_analysis


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Imatest SFRreg batch analysis")
    parser.add_argument("--input", required=True, help="Input folder Imatest_data_<EVENT>")
    parser.add_argument("--output", required=True, help="Output folder")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    input_path = Path(args.input)
    output_path = Path(args.output)

    run_analysis(input_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
