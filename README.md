# Hydra Experiment Search

`hydra-experiment-search` is a reusable experiment browser for Python projects that save Hydra outputs with resolved configs.

It indexes runs by scanning for resolved config files, flattens the config into searchable keys, and exposes:

- a CLI search tool
- a browser-based search UI
- a small Python API for indexing, parsing, and web-handler setup

It is designed to work independently of any specific training or simulation codebase. If your repository uses Hydra and writes per-run configs, this package can index and browse those runs.

## What it assumes

By default, the package looks for:

- `**/results/resolved_config.yaml`

This matches a common Hydra workflow where a run directory contains a `results/` subdirectory with a copied or resolved config. If your layout differs, override:

- `--config-glob`
- `--config-name`

## Install

From the package directory:

```bash
cd /home/mwkim/hydra-experiment-search
pip install -e .
```

From GitHub:

```bash
pip install git+https://github.com/miinukim/hydra-experiment-search.git
```

Requirements:

- Python 3.10+
- `hydra-core>=1.3`

## Python API

```python
from hydra_experiment_search import filter_experiments, index_experiments

records = index_experiments("outputs")
matches = filter_experiments(records, ["model.depth=6", "trainer.max_epochs>=50"])
```

For embedding in another repo or tool:

```python
from hydra_experiment_search import build_web_handler, parse_cli_args

args = parse_cli_args(["--root", "outputs", "model.depth=6"])
handler_cls = build_web_handler(root="outputs", config_glob="**/.hydra/config.yaml", config_name="config.yaml")
```

You can also start the web server programmatically:

```python
from hydra_experiment_search import serve

serve(
    host="127.0.0.1",
    port=8765,
    root="outputs",
    config_glob="**/.hydra/config.yaml",
    config_name="config.yaml",
)
```

## CLI

```bash
hydra-experiment-search --root outputs model.depth=6 trainer.max_epochs>=50
```

Typical filters:

- `model.depth=6`
- `trainer.max_epochs>=50`
- `optimizer.name=adamw`
- `dataset.name~cifar`

Show selected columns:

```bash
hydra-experiment-search \
  --root outputs \
  --show _date _time _run_dir model.depth trainer.max_epochs \
  model.depth=6
```

## Web UI

```bash
hydra-experiment-search-web --root outputs --host 127.0.0.1 --port 8765
```

The web UI supports:

- flat config-key search with autocomplete
- CSV previews
- artifact and plot preview
- in-page image lightbox
- browsing over SSH port forwarding

For SSH usage:

```bash
ssh -L 8765:127.0.0.1:8765 <server>
```

Then open `http://127.0.0.1:8765`.

Run as a module if console scripts are not on your path:

```bash
python -m hydra_experiment_search.web --root outputs
python -m hydra_experiment_search.cli --root outputs model.depth=6
```

## General integration steps

1. Ensure your repo writes one resolved Hydra config per run.
2. Decide the search root you want to scan, for example `outputs/`.
3. Identify the config file pattern for your project.
   Common choices are `**/results/resolved_config.yaml` or `**/.hydra/config.yaml`.
4. Install the package into the same Python environment as your project.
5. Run either the CLI or web UI against that root and config pattern.
6. If needed, embed the parser or web handler into your own launcher script.

## Supported output layouts

Common layouts that work well:

1. A run directory with `results/resolved_config.yaml`
2. A Hydra run directory with `.hydra/config.yaml`
3. Any other layout where one config file per run can be matched by `--config-glob`

Examples:

```bash
hydra-experiment-search \
  --root outputs \
  --config-glob '**/results/resolved_config.yaml'
```

```bash
hydra-experiment-search \
  --root outputs \
  --config-glob '**/.hydra/config.yaml'
```

## Custom layouts

If your project stores configs somewhere else, point the package at the right file pattern:

```bash
hydra-experiment-search \
  --root outputs \
  --config-glob '**/.hydra/config.yaml' \
  trainer.max_epochs>=50
```

```bash
hydra-experiment-search-web \
  --root outputs \
  --config-glob '**/.hydra/config.yaml' \
  --config-name config.yaml
```

## qrcdim example

Use the standalone tool against `qrcdim` outputs:

```bash
hydra-experiment-search-web \
  --root /home/mwkim/qrc/qrcdim/experiments/outputs
```

Or, if the runs store Hydra configs under `.hydra`:

```bash
hydra-experiment-search-web \
  --root /home/mwkim/qrc/qrcdim/experiments/outputs \
  --config-glob '**/.hydra/config.yaml' \
  --config-name config.yaml
```

## Development

Editable install:

```bash
pip install -e .
```

Basic sanity checks:

```bash
python -m py_compile hydra_experiment_search/*.py
python -m hydra_experiment_search.cli --help
python -m hydra_experiment_search.web --help
```
