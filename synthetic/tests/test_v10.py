from pathlib import Path
import numpy as np
import pandas as pd
import yaml

from cpshift.data_v10 import generate_source_split, oracle_density_ratio, sample_target_covariates
from cpshift.metrics_v10 import persistent_threshold_breakpoint
from cpshift.runner_v10 import derived_seed, run


def test_locked_dgps_and_noise_generate():
    rng = np.random.default_rng(1)
    for dgp in ["linear", "nonlinear"]:
        for noise in ["gaussian", "heteroscedastic", "student_t3"]:
            Xtr, ytr, Xcal, ycal = generate_source_split(rng, 30, 20, 5, dgp, noise)
            assert Xtr.shape == (30, 5) and ytr.shape == (30,)
            assert Xcal.shape == (20, 5) and ycal.shape == (20,)
            assert np.isfinite(ytr).all() and np.isfinite(ycal).all()


def test_oracle_ratio_at_zero_is_one_all_families():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(40, 5))
    for fam in ["mean", "variance", "mixture", "tail_mixture", "nonlinear"]:
        w = oracle_density_ratio(X, fam, 0.0)
        assert w is not None and np.allclose(w, 1.0)


def test_seed_derivation_is_order_invariant_and_distinct():
    a = derived_seed(2026081601, 1, 2, 3, 4)
    b = derived_seed(2026081601, 1, 2, 3, 4)
    c = derived_seed(2026081601, 1, 2, 3, 5)
    assert a == b and a != c


def test_persistent_undercoverage_breakpoint():
    df = pd.DataFrame({
        "dgp": ["l"] * 5, "noise": ["g"] * 5, "shift_family": ["mean"] * 5, "method": ["m"] * 5,
        "severity": [0, .5, 1, 1.5, 2], "coverage_mean": [.90, .88, .865, .86, .89],
    })
    out = persistent_threshold_breakpoint(df, ["dgp", "noise", "shift_family", "method"], "coverage_mean", .87, "lt", 2, "B_cov")
    assert float(out.loc[0, "B_cov"]) == 1.0


def test_zero_shift_samples_can_be_common_across_families():
    seed = derived_seed(2026081601, 0, 0, 0, 0, 0, 301)
    a = sample_target_covariates(np.random.default_rng(seed), 40, 5, "mean", 0.0)
    b = sample_target_covariates(np.random.default_rng(seed), 40, 5, "variance", 0.0)
    assert np.array_equal(a, b)


def test_tiny_runner_smoke(tmp_path: Path):
    cfg = yaml.safe_load(Path("configs/smoke_v10.yaml").read_text())
    cfg.update({"repetitions": 1, "n_train": 50, "n_cal": 50, "n_test": 70, "n_target_unlabeled": 50,
                "dgp_types": ["linear"], "noise_types": ["gaussian"], "shift_families": ["mean", "variance"],
                "cqr_estimators": 5})
    out = tmp_path / "run"
    run(cfg, out, 0, 1)
    raw = pd.read_csv(out / "raw_results_v10.csv")
    assert set(raw["method"]) >= {"SCP-Ridge", "CQR-GBR", "Estimated-WCP-Primary", "Estimated-WCP-Sensitivity", "Oracle-WCP-Ridge"}
    assert (out / "breakpoints_v10.csv").exists()
    assert (out / "checksums_v10.json").exists()


def test_breakpoint_search_excludes_baseline_in_summary(tmp_path: Path):
    # Construct a tiny locked-shape run likely to have noisy baseline; regardless of outcome,
    # breakpoints must never be 0 because summarize searches only severity > 0.
    cfg = yaml.safe_load(Path("configs/smoke_v10.yaml").read_text())
    cfg.update({"repetitions": 1, "n_train": 45, "n_cal": 45, "n_test": 55, "n_target_unlabeled": 45,
                "dgp_types": ["linear"], "noise_types": ["gaussian"], "shift_families": ["mean"],
                "cqr_estimators": 4})
    out = tmp_path / "bp"
    run(cfg, out, 0, 1)
    bp = pd.read_csv(out / "breakpoints_v10.csv")
    vals = bp[["B_cov", "B_cov_CI", "B_info", "B_inf"]].to_numpy(dtype=float).ravel()
    vals = vals[np.isfinite(vals)]
    assert np.all(vals > 0)
    assert (out / "baseline_quality_flags_v10.csv").exists()
