from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

@dataclass(frozen=True)
class ShiftBasis:
    scaler_mean: np.ndarray
    scaler_scale: np.ndarray
    direction: np.ndarray
    score_mean: float
    score_sd: float
    clip: float = 3.0

    def transform_features(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return (X - self.scaler_mean) / self.scaler_scale

    def score(self, X: np.ndarray) -> np.ndarray:
        z = self.transform_features(X)
        raw = z @ self.direction
        s = (raw - self.score_mean) / self.score_sd
        return np.clip(s, -self.clip, self.clip)


def fit_directional_basis(X_train: np.ndarray, clip: float = 3.0) -> ShiftBasis:
    X = np.asarray(X_train, dtype=float)
    scaler = StandardScaler().fit(X)
    z = scaler.transform(X)
    pca = PCA(n_components=1, svd_solver="full").fit(z)
    v = pca.components_[0].copy()
    # Explicitly orient the otherwise sign-indeterminate PC1.
    anchor = int(np.argmax(np.abs(v)))
    if v[anchor] < 0:
        v *= -1.0
    raw = z @ v
    mu = float(raw.mean())
    sd = float(raw.std(ddof=0))
    if not np.isfinite(sd) or sd <= 1e-12:
        raise ValueError("PC1 score variance is too small for tilt construction")
    scale = np.where(scaler.scale_ == 0, 1.0, scaler.scale_)
    return ShiftBasis(scaler.mean_.copy(), scale.copy(), v, mu, sd, float(clip))


def fit_radial_basis(X_train: np.ndarray, clip: float = 3.0):
    X = np.asarray(X_train, dtype=float)
    scaler = StandardScaler().fit(X)
    z = scaler.transform(X)
    raw = np.mean(z * z, axis=1)
    mu = float(raw.mean())
    sd = float(raw.std(ddof=0))
    if not np.isfinite(sd) or sd <= 1e-12:
        raise ValueError("Radial score variance is too small")
    scale = np.where(scaler.scale_ == 0, 1.0, scaler.scale_)
    return {
        "scaler_mean": scaler.mean_.copy(),
        "scaler_scale": scale.copy(),
        "score_mean": mu,
        "score_sd": sd,
        "clip": float(clip),
    }


def radial_score(X: np.ndarray, basis: dict) -> np.ndarray:
    z = (np.asarray(X, float) - basis["scaler_mean"]) / basis["scaler_scale"]
    raw = np.mean(z * z, axis=1)
    s = (raw - basis["score_mean"]) / basis["score_sd"]
    return np.clip(s, -basis["clip"], basis["clip"])


def normalized_tilt_weights(scores: np.ndarray, lam: float) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    logw = float(lam) * scores
    logw = logw - np.max(logw)
    w = np.exp(logw)
    m = float(w.mean())
    if not np.isfinite(m) or m <= 0:
        raise ValueError("Invalid tilt normalization")
    return w / m


def ess_ratio(weights: np.ndarray) -> float:
    w = np.asarray(weights, dtype=float)
    denom = float(np.sum(w * w))
    if denom <= 0:
        return float("nan")
    ess = float(np.sum(w) ** 2 / denom)
    return ess / len(w)


def paired_split_indices(n: int, seed: int, train_frac=0.40, cal_frac=0.25):
    if n < 10:
        raise ValueError("Dataset too small")
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    n_train = int(np.floor(train_frac * n))
    n_cal = int(np.floor(cal_frac * n))
    if n_train <= 0 or n_cal <= 0 or n_train + n_cal >= n:
        raise ValueError("Invalid split fractions")
    return perm[:n_train], perm[n_train:n_train+n_cal], perm[n_train+n_cal:]


def sample_target_indices(reservoir_size: int, probabilities: np.ndarray, n_draws: int, seed: int):
    p = np.asarray(probabilities, dtype=float)
    if len(p) != reservoir_size:
        raise ValueError("Probability length mismatch")
    if np.any(p < 0) or not np.all(np.isfinite(p)) or p.sum() <= 0:
        raise ValueError("Invalid sampling probabilities")
    p = p / p.sum()
    rng = np.random.default_rng(seed)
    idx = rng.choice(reservoir_size, size=int(n_draws), replace=True, p=p)
    unique_fraction = float(len(np.unique(idx)) / len(idx))
    return idx, unique_fraction


def derive_seed(master_seed: int, dataset_index: int, rep: int, severity_index: int, stream: int) -> int:
    ss = np.random.SeedSequence([master_seed, dataset_index, rep, severity_index, stream])
    return int(ss.generate_state(1, dtype=np.uint32)[0])


def tilt_ratio(scores: np.ndarray, lam: float) -> np.ndarray:
    """Unnormalized q/p proportionality on a common scale for all evaluated X.

    Scores are pre-clipped by the locked basis, so lambda<=2 yields a safe range.
    The unknown partition constant is common to calibration and test weights and
    therefore cancels from weighted conformal calculations.
    """
    scores = np.asarray(scores, dtype=float)
    return np.exp(float(lam) * scores)


def tilt_sampling_probabilities(scores: np.ndarray, lam: float) -> np.ndarray:
    w = tilt_ratio(scores, lam)
    total = float(w.sum())
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Invalid tilt sampling weights")
    return w / total
