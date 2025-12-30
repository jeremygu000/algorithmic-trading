from __future__ import annotations
import pandas as pd


def apply_constraints(
    w: pd.Series,
    max_single: float,
    max_core: float,
    core_symbols: list[str],
) -> pd.Series:
    w = w.clip(lower=0.0)
    if w.sum() == 0:
        return w
    w = w / w.sum()

    # cap single
    w = w.clip(upper=max_single)
    if w.sum() > 0:
        w = w / w.sum()

    # cap core sum
    core = [s for s in core_symbols if s in w.index]
    core_sum = w.loc[core].sum() if core else 0.0
    if core and core_sum > max_core:
        scale = max_core / core_sum
        w.loc[core] *= scale

        rest = w.drop(core, errors="ignore")
        rest_sum = rest.sum()
        if rest_sum > 0:
            w.loc[rest.index] *= (1 - max_core) / rest_sum
        else:
            w.loc[core] /= w.loc[core].sum()

    return w
