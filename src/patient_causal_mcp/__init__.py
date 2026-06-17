"""Bundled patient causal analysis MCP server."""

DEFAULT_DATASET_ID = "patient_001_100_days"

__all__ = ["DEFAULT_DATASET_ID", "load_bundled_dataset"]
__version__ = "0.1.0"


def __getattr__(name: str):
    """Lazily expose heavier dataset helpers without importing pandas at startup."""

    if name == "load_bundled_dataset":
        from patient_causal_mcp.datasets import load_bundled_dataset

        return load_bundled_dataset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
