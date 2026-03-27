from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import re
from typing import Any, Iterable

from omegaconf import OmegaConf


DEFAULT_CONFIG_GLOB = "**/results/resolved_config.yaml"
DEFAULT_CONFIG_NAME = "resolved_config.yaml"
IMAGE_SUFFIXES = {"png", "jpg", "jpeg", "svg", "gif", "webp"}
FILTER_PATTERN = re.compile(r"^(?P<key>.+?)(?P<op>!=|>=|<=|=|>|<|~)(?P<value>.+)$")


@dataclass
class ExperimentRecord:
    data: dict[str, Any]


def _flatten(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            _flatten(name, child, out)
        return
    if isinstance(value, list):
        out[prefix] = value
        return
    out[prefix] = value


def _parse_value(text: str) -> Any:
    lowered = text.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in text or "e" in lowered:
            return float(text)
        return int(text)
    except ValueError:
        return text.strip()


def _csv_metadata(results_dir: Path) -> dict[str, Any]:
    csv_paths = sorted(results_dir.glob("*.csv"))
    meta: dict[str, Any] = {
        "_csv_files": [path.name for path in csv_paths],
        "_csv_count": len(csv_paths),
    }
    for path in csv_paths:
        with path.open(newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        meta[f"_csv_rows.{path.name}"] = max(0, len(rows) - 1)
        meta[f"_csv_columns.{path.name}"] = rows[0] if rows else []
    return meta


def index_experiments(
    root: str | Path,
    config_glob: str = DEFAULT_CONFIG_GLOB,
    config_name: str = DEFAULT_CONFIG_NAME,
) -> list[ExperimentRecord]:
    root_path = Path(root).expanduser().resolve()
    records: list[ExperimentRecord] = []
    for config_path in sorted(root_path.glob(config_glob)):
        results_dir = config_path.parent
        run_dir = results_dir.parent
        resolved = OmegaConf.to_container(OmegaConf.load(config_path), resolve=True)
        flat: dict[str, Any] = {}
        _flatten("", resolved, flat)
        timestamp_parts = run_dir.parts[-2:] if len(run_dir.parts) >= 2 else ("", "")
        flat.update(
            {
                "_run_dir": str(run_dir),
                "_results_dir": str(results_dir),
                "_config_path": str(config_path),
                "_config_name": config_name,
                "_date": timestamp_parts[0],
                "_time": timestamp_parts[1],
            }
        )
        flat.update(_csv_metadata(results_dir))
        records.append(ExperimentRecord(flat))
    return records


def load_experiment_details(
    results_dir: str | Path,
    row_limit: int = 20,
    config_name: str = DEFAULT_CONFIG_NAME,
) -> dict[str, Any]:
    results_path = Path(results_dir).expanduser().resolve()
    csv_tables: list[dict[str, Any]] = []
    for path in sorted(results_path.glob("*.csv")):
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for idx, row in enumerate(reader):
                if idx >= row_limit:
                    break
                rows.append(row)
        csv_tables.append(
            {
                "name": path.name,
                "columns": list(rows[0].keys()) if rows else [],
                "rows": rows,
                "row_limit": row_limit,
            }
        )

    artifacts = []
    for path in sorted(results_path.iterdir()):
        if path.name == config_name or path.suffix.lower() == ".csv":
            continue
        artifacts.append(
            {
                "name": path.name,
                "path": str(path),
                "type": path.suffix.lower().lstrip("."),
                "is_image": path.suffix.lower().lstrip(".") in IMAGE_SUFFIXES,
            }
        )

    config_path = results_path / config_name
    config_text = config_path.read_text() if config_path.exists() else ""
    return {
        "results_dir": str(results_path),
        "config_name": config_name,
        "config_text": config_text,
        "csv_tables": csv_tables,
        "artifacts": artifacts,
    }


def parse_filter(expr: str) -> tuple[str, str, Any]:
    match = FILTER_PATTERN.match(expr.strip())
    if match is None:
        raise ValueError(f"Invalid filter expression '{expr}'")
    key = match.group("key").strip()
    op = match.group("op")
    value = _parse_value(match.group("value"))
    return key, op, value


def _compare(left: Any, op: str, right: Any) -> bool:
    if op == "~":
        return str(right).lower() in str(left).lower()
    if op == "=":
        return left == right
    if op == "!=":
        return left != right
    if op == ">":
        return float(left) > float(right)
    if op == "<":
        return float(left) < float(right)
    if op == ">=":
        return float(left) >= float(right)
    if op == "<=":
        return float(left) <= float(right)
    raise ValueError(f"Unsupported operator '{op}'")


def filter_experiments(records: Iterable[ExperimentRecord], expressions: Iterable[str]) -> list[ExperimentRecord]:
    parsed = [parse_filter(expr) for expr in expressions if expr.strip()]
    if not parsed:
        return list(records)

    matched: list[ExperimentRecord] = []
    for record in records:
        ok = True
        for key, op, value in parsed:
            if key not in record.data:
                ok = False
                break
            try:
                if not _compare(record.data[key], op, value):
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            matched.append(record)
    return matched


def summarize_fields(records: Iterable[ExperimentRecord], max_values_per_field: int = 12) -> dict[str, Any]:
    value_map: dict[str, set[str]] = {}
    numeric_keys: set[str] = set()
    for record in records:
        for key, value in record.data.items():
            if key.startswith("_"):
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_keys.add(key)
            if isinstance(value, (str, int, float, bool)):
                bucket = value_map.setdefault(key, set())
                if len(bucket) < max_values_per_field:
                    bucket.add(str(value))
    return {
        "keys": sorted(value_map.keys()),
        "numeric_keys": sorted(numeric_keys),
        "sample_values": {key: sorted(values) for key, values in sorted(value_map.items())},
    }
