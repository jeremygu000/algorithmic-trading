"""Utilities for symbol list file read/write."""

from __future__ import annotations

import re
from pathlib import Path

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.\-^]{1,15}$")


def _normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    if not SYMBOL_PATTERN.match(s):
        raise ValueError(f"非法股票代码: {symbol}")
    return s


def resolve_symbol_file(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def read_symbol_file(path_value: str) -> list[str]:
    path = resolve_symbol_file(path_value)
    if not path.exists():
        return []

    symbols: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            symbols.append(_normalize_symbol(line))
        except ValueError:
            # Ignore malformed lines to keep file fault-tolerant.
            continue

    # 去重保序
    return list(dict.fromkeys(symbols))


def write_symbol_file(path_value: str, symbols: list[str]) -> list[str]:
    path = resolve_symbol_file(path_value)
    normalized = []
    for sym in symbols:
        normalized.append(_normalize_symbol(sym))
    unique_symbols = list(dict.fromkeys(normalized))

    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(unique_symbols)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")
    return unique_symbols


def add_symbol_to_file(path_value: str, symbol: str) -> list[str]:
    current = read_symbol_file(path_value)
    normalized = _normalize_symbol(symbol)
    if normalized not in current:
        current.append(normalized)
    return write_symbol_file(path_value, current)


def remove_symbol_from_file(path_value: str, symbol: str) -> list[str]:
    normalized = _normalize_symbol(symbol)
    current = [s for s in read_symbol_file(path_value) if s != normalized]
    return write_symbol_file(path_value, current)
