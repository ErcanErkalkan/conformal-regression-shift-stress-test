from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from scipy.stats import kendalltau


def persistent_threshold_breakpoint(
    summary: pd.DataFrame,
    group_cols: list[str],
    metric: str,
    threshold: float,
    direction: str,
    persistence: int = 2,
    output_name: str = "breakpoint",
) -> pd.DataFrame:
    """Return first severity starting a persistent threshold run.

    direction='lt' means metric < threshold; 'le', 'gt', 'ge' are also supported.
    """
    if persistence < 1:
        raise ValueError("persistence must be >=1")
    ops = {
        "lt": lambda x: x < threshold,
        "le": lambda x: x <= threshold,
        "gt": lambda x: x > threshold,
        "ge": lambda x: x >= threshold,
    }
    if direction not in ops:
        raise ValueError(f"unknown direction: {direction}")
    rows = []
    for key, g in summary.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        g = g.sort_values("severity")
        vals = g[metric].to_numpy(dtype=float)
        sev = g["severity"].to_numpy(dtype=float)
        fail = np.asarray(ops[direction](vals), dtype=bool) & np.isfinite(vals)
        bp = np.nan
        if len(fail) >= persistence:
            run = np.convolve(fail.astype(int), np.ones(persistence, dtype=int), mode="valid")
            idx = np.flatnonzero(run == persistence)
            if idx.size:
                bp = float(sev[idx[0]])
        row = {c: v for c, v in zip(group_cols, key)}
        row[output_name] = bp
        rows.append(row)
    return pd.DataFrame(rows)


def metric_rank_reversals(
    summary: pd.DataFrame,
    group_cols: list[str],
    methods: list[str],
    metric: str,
    require_all_zero_infinite: bool = False,
) -> pd.DataFrame:
    """Compare method order at each severity with severity 0 within each group.

    Smaller metric values are better. Ties are explicit and omitted from pairwise-reversal denominators.
    """
    rows = []
    for key, g in summary.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        g = g[g["method"].isin(methods)]
        severities = sorted(g["severity"].unique())
        if not severities or 0.0 not in severities:
            continue

        def vector(s: float, col: str) -> pd.Series | None:
            gg = g[g["severity"] == s].set_index("method")
            if not all(m in gg.index for m in methods):
                return None
            return gg.loc[methods, col].astype(float)

        base = vector(0.0, metric)
        if base is None:
            continue
        for s in severities:
            cur = vector(float(s), metric)
            if cur is None:
                continue
            if require_all_zero_infinite:
                inf = vector(float(s), "infinite_fraction_mean")
                if inf is None or np.any(inf.to_numpy(dtype=float) > 1e-12):
                    continue
            reversals = comparable = 0
            for a, b in itertools.combinations(methods, 2):
                d0 = float(base[a] - base[b])
                ds = float(cur[a] - cur[b])
                if not np.isfinite(d0) or not np.isfinite(ds) or abs(d0) < 1e-12 or abs(ds) < 1e-12:
                    continue
                comparable += 1
                if d0 * ds < 0:
                    reversals += 1
            base_rank = base.rank(method="average").to_numpy(dtype=float)
            cur_rank = cur.rank(method="average").to_numpy(dtype=float)
            tau = kendalltau(base_rank, cur_rank, variant="b").statistic
            row = {c: v for c, v in zip(group_cols, key)}
            row.update({
                "metric": metric,
                "severity": float(s),
                "pairwise_reversal_count": reversals,
                "comparable_pairs": comparable,
                "reversal_fraction": reversals / comparable if comparable else np.nan,
                "kendall_tau_vs_baseline": float(tau) if np.isfinite(tau) else np.nan,
                "order": " > ".join(cur.sort_values().index.tolist()),
            })
            rows.append(row)
    return pd.DataFrame(rows)


def trajectory_integrals(raw: pd.DataFrame) -> pd.DataFrame:
    """Per-repetition trapezoidal integrals along each native shift trajectory."""
    rows = []
    group_cols = ["rep", "dgp", "noise", "shift_family", "method"]
    for key, g in raw.groupby(group_cols, dropna=False):
        g = g.sort_values("severity")
        x = g["severity"].to_numpy(dtype=float)
        if len(np.unique(x)) < 2:
            continue
        row = {c: v for c, v in zip(group_cols, key)}
        for col, out in [
            ("coverage_deficit", "auc_coverage_deficit"),
            ("coverage_gap", "auc_coverage_gap"),
            ("infinite_interval_fraction", "auc_infinite_fraction"),
        ]:
            y = g[col].to_numpy(dtype=float)
            row[out] = float(np.trapezoid(y, x)) if np.all(np.isfinite(y)) else np.nan
        # ESS ratio is defined for all methods in our schema (1 for unweighted methods).
        y = g["ess_ratio"].to_numpy(dtype=float)
        row["auc_information_loss"] = float(np.trapezoid(1.0 - y, x)) if np.all(np.isfinite(y)) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
