from __future__ import annotations
from pathlib import Path
import pandas as pd


def cache_path(cache_dir: str, key: str) -> Path:
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return Path(cache_dir) / f"{key}.parquet"


def load_parquet(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_parquet(path)
    return None


def save_parquet(path: Path, df: pd.DataFrame) -> None:
    df.to_parquet(path)
