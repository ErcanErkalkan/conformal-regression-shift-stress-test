from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
import yaml
from scipy.stats import t

from .conformal import ConformalizedQuantileRegressor, OracleWeightedSplitConformalRidge, SplitConformalRidge
from .data_v10 import generate_source_split, generate_target, oracle_density_ratio, sample_target_covariates
from .density_ratio import ClassifierDensityRatio
from .metrics import interval_metrics, normalized_weight_error, rbf_mmd2, weight_diagnostics
from .metrics_v10 import metric_rank_reversals, persistent_threshold_breakpoint, trajectory_integrals

VERSION = "1.0.1-locked"


def derived_seed(master: int, *coords: int) -> int:
    """Order- and shard-invariant uint32 seed derivation."""
    ss = np.random.SeedSequence([int(master), *[int(x) for x in coords]])
    return int(ss.generate_state(1, dtype=np.uint32)[0])




def config_hash(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def expected_raw_rows(cfg: dict, rep_count: int) -> int:
    nd = len(cfg["dgp_types"]); nn = len(cfg["noise_types"]); nf = len(cfg["shift_families"]); ns = len(cfg["severities"])
    # Four methods are always present: SCP, CQR, estimated-primary, estimated-sensitivity.
    base = 4 * nf * ns
    # Oracle WCP exists for all severities in four analytic families, and at delta=0 for nonlinear.
    analytic = {"mean", "variance", "mixture", "tail_mixture"}
    oracle = sum(ns if fam in analytic else 1 for fam in cfg["shift_families"])
    return int(rep_count) * nd * nn * (base + oracle)


def expected_seed_rows(cfg: dict, rep_count: int) -> int:
    return int(rep_count) * len(cfg["dgp_types"]) * len(cfg["noise_types"]) * len(cfg["shift_families"]) * len(cfg["severities"])

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_config(cfg: dict) -> None:
    required = [
        "seed", "alpha", "coverage_tolerance", "persistent_failure_points", "repetitions",
        "n_train", "n_cal", "n_test", "n_target_unlabeled", "n_features",
        "dgp_types", "noise_types", "shift_families", "severities",
        "primary_density_ratio", "sensitivity_density_ratio",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"missing config keys: {missing}")
    if float(cfg["alpha"]) != 0.1 and cfg.get("lock_mode", True):
        raise ValueError("locked primary core requires alpha=0.1")
    if cfg.get("lock_mode", True):
        if [float(x) for x in cfg["severities"]] != [0.0, 0.5, 1.0, 1.5, 2.0]:
            raise ValueError("locked primary core severity grid changed")
        if int(cfg["persistent_failure_points"]) != 2:
            raise ValueError("locked primary core persistence must be 2")


def _record(rows, base: dict, method: str, auc: float, mmd2: float, diag: dict, met: dict, werr: dict | None = None):
    d = {**base, "method": method, "shift_classifier_auc": auc, "mmd2": mmd2, **diag, **met}
    if werr:
        d.update(werr)
    rows.append(d)


def _paired_ci(raw: pd.DataFrame, a: str, b: str, value: str, label: str) -> list[dict]:
    rows = []
    keys = ["dgp", "noise", "shift_family", "severity"]
    pa = raw[raw.method == a][keys + ["rep", value]].rename(columns={value: "a"})
    pb = raw[raw.method == b][keys + ["rep", value]].rename(columns={value: "b"})
    m = pa.merge(pb, on=keys + ["rep"])
    for key, g in m.groupby(keys, dropna=False):
        dif = (g.a - g.b).to_numpy(dtype=float)
        dif = dif[np.isfinite(dif)]
        n = len(dif)
        if n == 0:
            continue
        mean = float(np.mean(dif))
        if n > 1:
            sd = float(np.std(dif, ddof=1)); se = sd / np.sqrt(n); crit = float(t.ppf(0.975, n - 1))
            lo, hi = mean - crit * se, mean + crit * se
        else:
            lo = hi = np.nan
        rows.append({
            "dgp": key[0], "noise": key[1], "shift_family": key[2], "severity": key[3],
            "comparison": label, "metric": value, "n_pairs": n, "mean_difference": mean,
            "ci95_low": lo, "ci95_high": hi,
        })
    return rows


def summarize(raw: pd.DataFrame, cfg: dict, out: Path) -> None:
    reps = raw["rep"].nunique()
    group = ["dgp", "noise", "shift_family", "method", "severity"]
    agg = raw.groupby(group, as_index=False).agg(
        coverage_mean=("coverage", "mean"), coverage_sd=("coverage", "std"),
        coverage_gap_mean=("coverage_gap", "mean"), coverage_deficit_mean=("coverage_deficit", "mean"),
        width_mean=("mean_width_finite", "mean"), interval_score_mean=("interval_score_finite", "mean"),
        infinite_fraction_mean=("infinite_interval_fraction", "mean"),
        ess_ratio_mean=("ess_ratio", "mean"), weight_cv_mean=("weight_cv", "mean"),
        max_normalized_weight_mean=("max_normalized_weight", "mean"), shift_auc_mean=("shift_classifier_auc", "mean"),
        mmd2_mean=("mmd2", "mean"), log_weight_rmse_mean=("log_weight_rmse", "mean"),
        log_weight_mae_mean=("log_weight_mae", "mean"), log_weight_corr_mean=("log_weight_corr", "mean"),
        est_to_oracle_ess_ratio_mean=("estimated_to_oracle_ess_ratio", "mean"),
    )
    agg["coverage_se"] = agg["coverage_sd"] / np.sqrt(reps)
    # t interval reflects finite Monte Carlo repetitions rather than asymptotic 1.96.
    crit = float(t.ppf(0.975, max(reps - 1, 1))) if reps > 1 else np.nan
    agg["coverage_ci95_low"] = np.clip(agg["coverage_mean"] - crit * agg["coverage_se"], 0.0, 1.0)
    agg["coverage_ci95_high"] = np.clip(agg["coverage_mean"] + crit * agg["coverage_se"], 0.0, 1.0)
    agg.to_csv(out / "summary_v10.csv", index=False)

    gcols = ["dgp", "noise", "shift_family", "method"]
    lower = (1.0 - float(cfg["alpha"])) - float(cfg["coverage_tolerance"])
    p = int(cfg["persistent_failure_points"])

    # Baseline quality is audited separately. A shift-induced breakpoint is searched only at severity > 0.
    base = agg[agg["severity"] == 0.0][gcols + ["coverage_mean", "coverage_ci95_high", "ess_ratio_mean", "infinite_fraction_mean"]].copy()
    base["baseline_undercoverage"] = base["coverage_mean"] < lower
    base["baseline_undercoverage_CI"] = base["coverage_ci95_high"] < lower
    base["baseline_info_fragile"] = base["ess_ratio_mean"] <= float(cfg["info_ess_ratio_threshold"])
    base["baseline_usability_issue"] = base["infinite_fraction_mean"] >= float(cfg["infinite_interval_threshold"])
    base.to_csv(out / "baseline_quality_flags_v10.csv", index=False)

    shifted = agg[agg["severity"] > 0.0].copy()
    b_cov = persistent_threshold_breakpoint(shifted, gcols, "coverage_mean", lower, "lt", p, "B_cov")
    b_cov_ci = persistent_threshold_breakpoint(shifted, gcols, "coverage_ci95_high", lower, "lt", p, "B_cov_CI")
    b_info = persistent_threshold_breakpoint(shifted, gcols, "ess_ratio_mean", float(cfg["info_ess_ratio_threshold"]), "le", p, "B_info")
    b_inf = persistent_threshold_breakpoint(shifted, gcols, "infinite_fraction_mean", float(cfg["infinite_interval_threshold"]), "ge", p, "B_inf")
    bp = b_cov.merge(b_cov_ci, on=gcols, how="outer").merge(b_info, on=gcols, how="outer").merge(b_inf, on=gcols, how="outer")
    bp.to_csv(out / "breakpoints_v10.csv", index=False)

    common = ["SCP-Ridge", "CQR-GBR", "Estimated-WCP-Primary"]
    rank_groups = ["dgp", "noise", "shift_family"]
    rank_frames = [
        metric_rank_reversals(agg, rank_groups, common, "coverage_deficit_mean"),
        metric_rank_reversals(agg, rank_groups, common, "coverage_gap_mean"),
        metric_rank_reversals(agg, rank_groups, common, "infinite_fraction_mean"),
        metric_rank_reversals(agg, rank_groups, common, "interval_score_mean", require_all_zero_infinite=True),
    ]
    pd.concat([x for x in rank_frames if not x.empty], ignore_index=True).to_csv(out / "rank_reversals_metric_specific_v10.csv", index=False)

    traj = trajectory_integrals(raw)
    traj.to_csv(out / "trajectory_metrics_v10.csv", index=False)

    pairs = []
    for metric in ["coverage", "coverage_deficit", "infinite_interval_fraction", "interval_score_finite", "ess_ratio"]:
        pairs += _paired_ci(raw, "Estimated-WCP-Primary", "Oracle-WCP-Ridge", metric, "Primary - Oracle")
        pairs += _paired_ci(raw, "Estimated-WCP-Sensitivity", "Oracle-WCP-Ridge", metric, "Sensitivity - Oracle")
        pairs += _paired_ci(raw, "Estimated-WCP-Primary", "Estimated-WCP-Sensitivity", metric, "Primary - Sensitivity")
        pairs += _paired_ci(raw, "Estimated-WCP-Primary", "SCP-Ridge", metric, "Primary - SCP")
    pd.DataFrame(pairs).to_csv(out / "paired_method_differences_v10.csv", index=False)


def run(cfg: dict, out: Path, rep_start: int = 0, rep_end: int | None = None) -> None:
    wall_start = time.perf_counter()
    _validate_config(cfg)
    out.mkdir(parents=True, exist_ok=True)
    total_reps = int(cfg["repetitions"])
    rep_end = total_reps if rep_end is None else min(int(rep_end), total_reps)
    rep_start = max(0, int(rep_start))
    if rep_start >= rep_end:
        raise ValueError("empty repetition shard")

    alpha = float(cfg["alpha"]); p = int(cfg["n_features"]); master = int(cfg["seed"])
    dgp_types = list(cfg["dgp_types"]); noise_types = list(cfg["noise_types"])
    fams = list(cfg["shift_families"]); sevs = [float(x) for x in cfg["severities"]]
    primary = cfg["primary_density_ratio"]; sensitivity = cfg["sensitivity_density_ratio"]
    rows: list[dict] = []; seed_rows: list[dict] = []

    for rep in range(rep_start, rep_end):
        for di, dgp in enumerate(dgp_types):
            for ni, noise in enumerate(noise_types):
                source_seed = derived_seed(master, rep, di, ni, 100)
                model_seed = derived_seed(master, rep, di, ni, 200)
                source_rng = np.random.default_rng(source_seed)
                Xtr, ytr, Xcal, ycal = generate_source_split(
                    source_rng, int(cfg["n_train"]), int(cfg["n_cal"]), p, dgp, noise
                )
                scp = SplitConformalRidge(alpha=alpha).fit(Xtr, ytr, Xcal, ycal)
                basew = OracleWeightedSplitConformalRidge(alpha=alpha).fit(Xtr, ytr, Xcal, ycal)
                cqr = ConformalizedQuantileRegressor(
                    alpha=alpha, n_estimators=int(cfg["cqr_estimators"]), random_state=model_seed
                ).fit(Xtr, ytr, Xcal, ycal)

                # Cache the common no-shift samples so every trajectory has the same δ=0 anchor.
                baseline_u_seed = derived_seed(master, rep, di, ni, 0, 0, 301)
                baseline_t_seed = derived_seed(master, rep, di, ni, 0, 0, 302)
                baseline_Xu = sample_target_covariates(np.random.default_rng(baseline_u_seed), int(cfg["n_target_unlabeled"]), p, fams[0], 0.0)
                baseline_Xt, baseline_yt = generate_target(np.random.default_rng(baseline_t_seed), int(cfg["n_test"]), p, fams[0], 0.0, dgp, noise)

                for fi, fam in enumerate(fams):
                    for si, sev in enumerate(sevs):
                        if sev == 0.0:
                            Xu, Xt, yt = baseline_Xu, baseline_Xt, baseline_yt
                            u_seed, t_seed = baseline_u_seed, baseline_t_seed
                        else:
                            u_seed = derived_seed(master, rep, di, ni, fi, si, 301)
                            t_seed = derived_seed(master, rep, di, ni, fi, si, 302)
                            Xu = sample_target_covariates(np.random.default_rng(u_seed), int(cfg["n_target_unlabeled"]), p, fam, sev)
                            Xt, yt = generate_target(np.random.default_rng(t_seed), int(cfg["n_test"]), p, fam, sev, dgp, noise)

                        seed_rows.append({
                            "rep": rep, "dgp": dgp, "noise": noise, "shift_family": fam, "severity": sev,
                            "source_seed": source_seed, "model_seed": model_seed,
                            "target_unlabeled_seed": u_seed, "target_test_seed": t_seed,
                        })
                        mmd = rbf_mmd2(Xtr, Xu, max_points=int(cfg.get("mmd_max_points", 250)))
                        base = {"rep": rep, "dgp": dgp, "noise": noise, "shift_family": fam, "severity": sev}
                        unweighted_diag = {"ess": len(Xcal), "ess_ratio": 1.0, "weight_cv": 0.0, "max_normalized_weight": 1.0 / len(Xcal)}

                        lo, hi = scp.predict_interval(Xt)
                        _record(rows, base, "SCP-Ridge", np.nan, mmd, unweighted_diag, interval_metrics(yt, lo, hi, alpha))
                        lo, hi = cqr.predict_interval(Xt)
                        _record(rows, base, "CQR-GBR", np.nan, mmd, unweighted_diag, interval_metrics(yt, lo, hi, alpha))

                        wo_cal = oracle_density_ratio(Xcal, fam, sev)
                        wo_test = oracle_density_ratio(Xt, fam, sev)
                        for spec, name, offset in [
                            (primary, "Estimated-WCP-Primary", 401),
                            (sensitivity, "Estimated-WCP-Sensitivity", 402),
                        ]:
                            est_seed = derived_seed(master, rep, di, ni, fi, si, offset)
                            est = ClassifierDensityRatio(
                                max_iter=int(cfg["density_ratio_max_iter"]), random_state=est_seed,
                                degree=int(spec["degree"]), C=float(spec["C"]),
                            ).fit(Xtr, Xu)
                            auc = est.heldout_auc(Xcal, Xt)
                            we_cal = est.ratio(Xcal); we_test = est.ratio(Xt)
                            diag = weight_diagnostics(we_cal)
                            werr = normalized_weight_error(we_cal, wo_cal) if wo_cal is not None else None
                            lo, hi = basew.predict_interval_weighted(Xt, we_cal, we_test)
                            _record(rows, base, name, auc, mmd, diag, interval_metrics(yt, lo, hi, alpha), werr)

                        if wo_cal is not None and wo_test is not None:
                            diag = weight_diagnostics(wo_cal)
                            lo, hi = basew.predict_interval_weighted(Xt, wo_cal, wo_test)
                            _record(rows, base, "Oracle-WCP-Ridge", np.nan, mmd, diag, interval_metrics(yt, lo, hi, alpha), {
                                "log_weight_rmse": 0.0, "log_weight_mae": 0.0, "log_weight_corr": 1.0,
                                "estimated_to_oracle_ess_ratio": 1.0,
                            })

    raw = pd.DataFrame(rows)
    shard_reps = rep_end - rep_start
    expected = expected_raw_rows(cfg, shard_reps)
    if len(raw) != expected:
        raise RuntimeError(f"raw row count mismatch: got {len(raw)}, expected {expected}")
    critical = ["coverage", "coverage_deficit", "infinite_interval_fraction", "ess_ratio"]
    if raw.empty or raw[critical].isna().any().any():
        raise RuntimeError("critical result columns contain NaN or no rows were produced")
    key_cols = ["rep", "dgp", "noise", "shift_family", "severity", "method"]
    if raw.duplicated(key_cols).any():
        raise RuntimeError("duplicate result keys detected")

    raw.to_csv(out / "raw_results_v10.csv", index=False)
    seed_df = pd.DataFrame(seed_rows).drop_duplicates()
    expected_seeds = expected_seed_rows(cfg, shard_reps)
    if len(seed_df) != expected_seeds:
        raise RuntimeError(f"seed-manifest row count mismatch: got {len(seed_df)}, expected {expected_seeds}")
    seed_df.to_csv(out / "seed_manifest_v10.csv", index=False)
    summarize(raw, cfg, out)

    package_root = Path(__file__).resolve().parents[2]
    code_hashes = {}
    for pth in sorted((package_root / "src" / "cpshift").glob("*.py")):
        code_hashes[str(pth.relative_to(package_root))] = _sha256(pth)
    manifest = {
        "version": VERSION,
        "rep_start": rep_start, "rep_end": rep_end,
        "config": cfg, "config_sha256": config_hash(cfg),
        "expected_raw_rows": expected, "expected_seed_rows": expected_seeds,
        "wall_clock_seconds": float(time.perf_counter() - wall_start),
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__,
        "code_hashes": code_hashes,
    }
    (out / "run_manifest_v10.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    checksums = []
    for pth in sorted(out.iterdir()):
        if pth.is_file() and pth.name != "checksums_v10.json":
            checksums.append({"file": pth.name, "sha256": _sha256(pth), "bytes": pth.stat().st_size})
    (out / "checksums_v10.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--rep-start", type=int, default=0)
    ap.add_argument("--rep-end", type=int, default=None)
    a = ap.parse_args()
    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    run(cfg, Path(a.output_dir), a.rep_start, a.rep_end)


if __name__ == "__main__":
    main()
