__all__ = [
    "ExperimentRecord",
    "filter_experiments",
    "index_experiments",
    "list_experiments",
    "load_experiment_details",
    "parse_filter",
    "parse_cli_args",
    "resolve_experiment_root",
    "parse_web_args",
    "summarize_fields",
    "build_web_handler",
    "serve",
]


def __getattr__(name: str):
    if name in __all__:
        if name in {
            "ExperimentRecord",
            "filter_experiments",
            "index_experiments",
            "list_experiments",
            "load_experiment_details",
            "parse_filter",
            "resolve_experiment_root",
            "summarize_fields",
        }:
            from . import index as _index

            return getattr(_index, name)
        if name in {"parse_cli_args"}:
            from . import cli as _cli

            return getattr(_cli, name)
        if name in {"parse_web_args", "build_web_handler", "serve"}:
            from . import web as _web

            return getattr(_web, name)
    raise AttributeError(name)
