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


def resolve_experiment_root(root: str | Path, experiment: str | None = None) -> Path:
    root_path = Path(root).expanduser().resolve()
    experiment_name = (experiment or "").strip()
    if not experiment_name:
        return root_path
    experiment_path = Path(experiment_name)
    if experiment_path.is_absolute() or len(experiment_path.parts) != 1 or experiment_name in {".", ".."}:
        raise ValueError(f"Invalid experiment name '{experiment_name}'")
    selected_root = (root_path / experiment_name).resolve()
    if root_path not in selected_root.parents:
        raise ValueError(f"Experiment path outside outputs root: '{experiment_name}'")
    return selected_root


def list_experiments(
    root: str | Path,
    config_glob: str = DEFAULT_CONFIG_GLOB,
) -> list[dict[str, Any]]:
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        return []
    experiments: list[dict[str, Any]] = []
    for child in sorted(path for path in root_path.iterdir() if path.is_dir()):
        config_count = sum(1 for _ in child.glob(config_glob))
        if config_count:
            experiments.append({"name": child.name, "path": str(child), "config_count": config_count})
    return experiments


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
        try:
            relative_parts = run_dir.relative_to(root_path).parts
        except ValueError:
            relative_parts = ()
        if len(relative_parts) >= 3:
            experiment_name = relative_parts[0]
            date, time = relative_parts[1], relative_parts[2]
        elif len(relative_parts) >= 2:
            experiment_name = root_path.name
            date, time = relative_parts[0], relative_parts[1]
        else:
            experiment_name = ""
            date, time = run_dir.parts[-2:] if len(run_dir.parts) >= 2 else ("", "")
        flat.update(
            {
                "_experiment": experiment_name,
                "_run_dir": str(run_dir),
                "_results_dir": str(results_dir),
                "_config_path": str(config_path),
                "_config_name": config_name,
                "_date": date,
                "_time": time,
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
