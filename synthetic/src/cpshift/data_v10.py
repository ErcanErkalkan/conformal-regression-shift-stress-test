from __future__ import annotations

import numpy as np


def mean_shift_vector(delta: float, p: int) -> np.ndarray:
    if p <= 0:
        raise ValueError("p must be positive")
    return np.full(p, float(delta) / np.sqrt(p), dtype=float)


def sample_source_covariates(rng: np.random.Generator, n: int, p: int) -> np.ndarray:
    return rng.normal(size=(int(n), int(p)))


def variance_scale(severity: float) -> float:
    """Locked v1.0 isotropic scale for the variance-shift family."""
    return float(np.exp(0.25 * float(severity)))


def mixture_params(severity: float, p: int) -> tuple[float, np.ndarray]:
    """Locked v1.0 shifted-component mixture parameters."""
    pi = min(0.20 * float(severity), 0.40)
    far_mu = mean_shift_vector(2.5, p)
    return float(pi), far_mu


def tail_mixture_params(severity: float) -> tuple[float, float]:
    """Locked v1.0 zero-centered Gaussian scale-mixture parameters."""
    pi = min(0.15 * float(severity), 0.30)
    return float(pi), 2.5


def sample_target_covariates(
    rng: np.random.Generator, n: int, p: int, family: str, severity: float
) -> np.ndarray:
    severity = float(severity)
    if severity == 0.0:
        return sample_source_covariates(rng, n, p)
    if family == "mean":
        return rng.normal(size=(n, p)) + mean_shift_vector(severity, p)
    if family == "variance":
        return rng.normal(scale=variance_scale(severity), size=(n, p))
    if family == "mixture":
        pi, far_mu = mixture_params(severity, p)
        z = rng.random(n) < pi
        X = rng.normal(size=(n, p))
        if np.any(z):
            X[z] += far_mu
        return X
    if family == "tail_mixture":
        pi, far_scale = tail_mixture_params(severity)
        z = rng.random(n) < pi
        X = rng.normal(size=(n, p))
        if np.any(z):
            X[z] = rng.normal(scale=far_scale, size=(int(np.sum(z)), p))
        return X
    if family == "nonlinear":
        z = rng.normal(size=(n, p))
        gamma = 0.35 * severity
        X = z.copy()
        if p < 2:
            raise ValueError("nonlinear shift requires at least two features")
        X[:, 0] = z[:, 0] + gamma * (z[:, 1] ** 2 - 1.0) / np.sqrt(2.0)
        return X
    raise ValueError(f"unknown shift family: {family}")


def response_signal(X: np.ndarray, dgp: str) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[1] < 5:
        raise ValueError("locked v1.0 response mechanisms require at least five features")
    if dgp == "linear":
        beta = np.array([1.5, -1.0, 0.75, 0.50, -0.25], dtype=float)
        return X[:, :5] @ beta
    if dgp == "nonlinear":
        return 2.0 * np.sin(X[:, 0]) + 0.5 * X[:, 1] ** 2 + X[:, 2] * X[:, 3] + 0.5 * X[:, 4]
    raise ValueError(f"unknown dgp: {dgp}")


def sample_response(rng: np.random.Generator, X: np.ndarray, dgp: str, noise: str) -> np.ndarray:
    signal = response_signal(X, dgp)
    if noise == "gaussian":
        eps = rng.normal(size=X.shape[0])
    elif noise == "heteroscedastic":
        sigma = 0.5 + 0.5 * np.abs(X[:, 0])
        eps = rng.normal(scale=sigma, size=X.shape[0])
    elif noise == "student_t3":
        # Student-t(df=3) has variance 3; divide by sqrt(3) for unit variance.
        eps = rng.standard_t(df=3, size=X.shape[0]) / np.sqrt(3.0)
    else:
        raise ValueError(f"unknown noise: {noise}")
    return signal + eps


def generate_source_split(
    rng: np.random.Generator, n_train: int, n_cal: int, p: int, dgp: str, noise: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X_train = sample_source_covariates(rng, n_train, p)
    X_cal = sample_source_covariates(rng, n_cal, p)
    y_train = sample_response(rng, X_train, dgp, noise)
    y_cal = sample_response(rng, X_cal, dgp, noise)
    return X_train, y_train, X_cal, y_cal


def generate_target(
    rng: np.random.Generator, n_test: int, p: int, family: str, severity: float, dgp: str, noise: str
) -> tuple[np.ndarray, np.ndarray]:
    X_test = sample_target_covariates(rng, n_test, p, family, severity)
    y_test = sample_response(rng, X_test, dgp, noise)
    return X_test, y_test


def oracle_density_ratio(X: np.ndarray, family: str, severity: float) -> np.ndarray | None:
    """Exact q_X/p_X for locked v1.0 families when analytically available."""
    X = np.asarray(X, dtype=float)
    p = X.shape[1]
    severity = float(severity)
    if severity == 0.0:
        return np.ones(X.shape[0], dtype=float)
    if family == "mean":
        mu = mean_shift_vector(severity, p)
        log_w = X @ mu - 0.5 * float(mu @ mu)
        return np.exp(np.clip(log_w, -60.0, 60.0))
    if family == "variance":
        s = variance_scale(severity)
        log_w = -p * np.log(s) + 0.5 * (1.0 - 1.0 / (s * s)) * np.sum(X * X, axis=1)
        return np.exp(np.clip(log_w, -60.0, 60.0))
    if family == "mixture":
        pi, far_mu = mixture_params(severity, p)
        log_component_ratio = X @ far_mu - 0.5 * float(far_mu @ far_mu)
        return (1.0 - pi) + pi * np.exp(np.clip(log_component_ratio, -60.0, 60.0))
    if family == "tail_mixture":
        pi, s = tail_mixture_params(severity)
        log_component_ratio = -p * np.log(s) + 0.5 * (1.0 - 1.0 / (s * s)) * np.sum(X * X, axis=1)
        return (1.0 - pi) + pi * np.exp(np.clip(log_component_ratio, -60.0, 60.0))
    if family == "nonlinear":
        return None
    raise ValueError(f"unknown shift family: {family}")
