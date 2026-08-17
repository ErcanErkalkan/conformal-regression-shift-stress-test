from __future__ import annotations

import itertools
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, pdist
from scipy.stats import kendalltau


def interval_metrics(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float) -> dict[str, float]:
    y = np.asarray(y)
    lo = np.asarray(lo)
    hi = np.asarray(hi)
    finite = np.isfinite(lo) & np.isfinite(hi)
    covered = (y >= lo) & (y <= hi)
    coverage = float(np.mean(covered))
    inf_fraction = float(1.0 - np.mean(finite))
    if np.any(finite):
        width = hi[finite] - lo[finite]
        mean_width = float(np.mean(width))
        median_width = float(np.median(width))
        yf, lf, hf = y[finite], lo[finite], hi[finite]
        score = (hf - lf).astype(float)
        below = yf < lf
        above = yf > hf
        score[below] += (2.0 / alpha) * (lf[below] - yf[below])
        score[above] += (2.0 / alpha) * (yf[above] - hf[above])
        interval_score = float(np.mean(score))
    else:
        mean_width = median_width = interval_score = float("inf")
    return {
        "coverage": coverage,
        "coverage_gap": abs(coverage - (1.0 - alpha)),
        "coverage_deficit": max(0.0, (1.0 - alpha) - coverage),
        "mean_width_finite": mean_width,
        "median_width_finite": median_width,
        "interval_score_finite": interval_score,
        "infinite_interval_fraction": inf_fraction,
    }


def weight_diagnostics(weights: np.ndarray) -> dict[str, float]:
    w = np.asarray(weights, dtype=float)
    sw = float(np.sum(w))
    ss = float(np.sum(w * w))
    ess = (sw * sw / ss) if ss > 0 else 0.0
    mean = float(np.mean(w))
    cv = float(np.std(w) / mean) if mean > 0 else float("inf")
    max_norm = float(np.max(w) / sw) if sw > 0 else float("nan")
    return {"ess": ess, "ess_ratio": ess / len(w), "weight_cv": cv, "max_normalized_weight": max_norm}


def effective_sample_size(weights: np.ndarray) -> float:
    return weight_diagnostics(weights)["ess"]


def normalized_weight_error(estimated: np.ndarray, oracle: np.ndarray, log_clip: float = 8.0) -> dict[str, float]:
    est = np.asarray(estimated, dtype=float)
    ora = np.asarray(oracle, dtype=float)
    if est.shape != ora.shape:
        raise ValueError("weight arrays must have equal shape")
    est = est / max(float(np.mean(est)), 1e-12)
    ora = ora / max(float(np.mean(ora)), 1e-12)
    le = np.clip(np.log(np.clip(est, 1e-12, None)), -log_clip, log_clip)
    lo = np.clip(np.log(np.clip(ora, 1e-12, None)), -log_clip, log_clip)
    rmse = float(np.sqrt(np.mean((le - lo) ** 2)))
    mae = float(np.mean(np.abs(le - lo)))
    if np.std(le) < 1e-12 or np.std(lo) < 1e-12:
        corr = np.nan
    else:
        corr = float(np.corrcoef(le, lo)[0, 1])
    ess_est = effective_sample_size(est)
    ess_ora = effective_sample_size(ora)
    return {
        "log_weight_rmse": rmse,
        "log_weight_mae": mae,
        "log_weight_corr": corr,
        "estimated_to_oracle_ess_ratio": ess_est / ess_ora if ess_ora > 0 else np.nan,
    }


def rbf_mmd2(X: np.ndarray, Y: np.ndarray, max_points: int = 300) -> float:
    """Biased RBF MMD^2 with pooled median heuristic; descriptive, not proposed as novel."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    if len(X) > max_points:
        X = X[np.linspace(0, len(X) - 1, max_points, dtype=int)]
    if len(Y) > max_points:
        Y = Y[np.linspace(0, len(Y) - 1, max_points, dtype=int)]
    Z = np.vstack([X, Y])
    d = pdist(Z, metric="sqeuclidean")
    positive = d[d > 0]
    med_sq = float(np.median(positive)) if positive.size else 1.0
    gamma = 1.0 / max(2.0 * med_sq, 1e-12)
    Kxx = np.exp(-gamma * cdist(X, X, metric="sqeuclidean"))
    Kyy = np.exp(-gamma * cdist(Y, Y, metric="sqeuclidean"))
    Kxy = np.exp(-gamma * cdist(X, Y, metric="sqeuclidean"))
    return float(max(0.0, Kxx.mean() + Kyy.mean() - 2.0 * Kxy.mean()))


def coverage_failure_breakpoint(summary: pd.DataFrame, nominal: float, tolerance: float, persistence: int = 2) -> pd.DataFrame:
    out = []
    keys = ["shift_family", "method"] if "shift_family" in summary.columns else ["method"]
    for key, g in summary.groupby(keys):
        g = g.sort_values("severity")
        fail = (g["coverage_mean"].to_numpy() < (nominal - tolerance)).astype(int)
        sev = g["severity"].to_numpy(dtype=float)
        bp = np.nan
        if persistence <= 1:
            idx = np.flatnonzero(fail)
        else:
            run = np.convolve(fail, np.ones(persistence, dtype=int), mode="valid")
            idx = np.flatnonzero(run == persistence)
        if idx.size:
            bp = float(sev[idx[0]])
        row = dict(zip(keys, key)) if isinstance(key, tuple) else {keys[0]: key}
        row["coverage_failure_breakpoint"] = bp
        out.append(row)
    return pd.DataFrame(out)


def pairwise_rank_reversals(summary: pd.DataFrame, common_methods: list[str], metric: str = "coverage_gap_mean") -> pd.DataFrame:
    """Metric-specific pairwise reversal analysis. Smaller metric value is better."""
    rows = []
    for family, gf in summary.groupby("shift_family"):
        piv = gf[gf["method"].isin(common_methods)].pivot(index="method", columns="severity", values=metric)
        if not all(m in piv.index for m in common_methods):
            continue
        severities = sorted(piv.columns)
        base_values = piv[severities[0]]
        for s in severities:
            cur = piv[s]
            reversals = comparable = 0
            for a, b in itertools.combinations(common_methods, 2):
                d0 = float(base_values[a] - base_values[b])
                ds = float(cur[a] - cur[b])
                if abs(d0) < 1e-10 or not np.isfinite(d0) or not np.isfinite(ds):
                    continue
                comparable += 1
                if d0 * ds < 0:
                    reversals += 1
            base_rank = base_values.rank(method="average").loc[common_methods].to_numpy()
            cur_rank = cur.rank(method="average").loc[common_methods].to_numpy()
            tau = kendalltau(base_rank, cur_rank).statistic
            rows.append({
                "shift_family": family,
                "metric": metric,
                "severity": float(s),
                "pairwise_reversal_count": reversals,
                "comparable_pairs": comparable,
                "reversal_fraction": reversals / comparable if comparable else 0.0,
                "kendall_tau_vs_baseline": float(tau) if np.isfinite(tau) else np.nan,
                "order": " > ".join(cur.sort_values().index.tolist()),
            })
    return pd.DataFrame(rows)


def lexicographic_usability_reversals(summary: pd.DataFrame, common_methods: list[str]) -> pd.DataFrame:
    """Operational ranking: lower infinite fraction first, then lower finite interval score.

    This is intentionally a transparent ordering rule, not a new scalar metric.
    """
    rows = []
    for family, gf in summary.groupby("shift_family"):
        sev = sorted(gf["severity"].unique())
        if not sev:
            continue
        def key_for(method: str, s: float):
            r = gf[(gf.method == method) & (gf.severity == s)]
            if len(r) != 1:
                return None
            rr = r.iloc[0]
            return (float(rr["infinite_fraction_mean"]), float(rr["interval_score_mean"]))
        base = {m: key_for(m, sev[0]) for m in common_methods}
        if any(v is None for v in base.values()):
            continue
        for s in sev:
            cur = {m: key_for(m, s) for m in common_methods}
            if any(v is None for v in cur.values()):
                continue
            rev = comp = 0
            for a, b in itertools.combinations(common_methods, 2):
                b0 = -1 if base[a] < base[b] else (1 if base[a] > base[b] else 0)
                bs = -1 if cur[a] < cur[b] else (1 if cur[a] > cur[b] else 0)
                if b0 == 0 or bs == 0:
                    continue
                comp += 1
                rev += int(b0 != bs)
            order = sorted(common_methods, key=lambda m: cur[m])
            rows.append({"shift_family": family, "metric": "lexicographic_usability", "severity": float(s),
                         "pairwise_reversal_count": rev, "comparable_pairs": comp,
                         "reversal_fraction": rev / comp if comp else 0.0, "kendall_tau_vs_baseline": np.nan,
                         "order": " > ".join(order)})
    return pd.DataFrame(rows)
