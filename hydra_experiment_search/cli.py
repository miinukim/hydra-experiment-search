from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

DEFAULT_CONFIG_GLOB = "**/results/resolved_config.yaml"
DEFAULT_ROOT = "/home/mwkim/qrc/experiments/outputs/"


DEFAULT_COLUMNS = [
    "_date",
    "_time",
    "_run_dir",
    "_csv_files",
]


def _format_value(value: object) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def build_parser(default_root: str = DEFAULT_ROOT) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search Hydra experiment outputs by resolved config fields.",
    )
    parser.add_argument(
        "--root",
        default=default_root,
        help="Root directory to scan for Hydra outputs.",
    )
    parser.add_argument(
        "--config-glob",
        default=DEFAULT_CONFIG_GLOB,
        help="Glob used to locate resolved config files under the root.",
    )
    parser.add_argument(
        "--show",
        nargs="*",
        default=DEFAULT_COLUMNS,
        help="Columns to print from the indexed experiment records.",
    )
    parser.add_argument(
        "filters",
        nargs="*",
        help="Filter expressions like model.depth=6 or trainer.epochs>=50",
    )
    return parser


def parse_cli_args(argv: Sequence[str] | None = None, default_root: str = DEFAULT_ROOT) -> argparse.Namespace:
    parser = build_parser(default_root=default_root)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, default_root: str = DEFAULT_ROOT) -> None:
    args = parse_cli_args(argv=argv, default_root=default_root)
    from .index import filter_experiments, index_experiments

    records = index_experiments(args.root, config_glob=args.config_glob)
    matches = filter_experiments(records, args.filters)

    print(f"Found {len(matches)} matching experiments under {Path(args.root).expanduser().resolve()}")
    print("\t".join(args.show))
    for record in matches:
        print("\t".join(_format_value(record.data.get(column, "")) for column in args.show))


if __name__ == "__main__":
    main()
