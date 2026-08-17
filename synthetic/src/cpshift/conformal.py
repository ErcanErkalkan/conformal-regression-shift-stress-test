from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    scores = np.asarray(scores, dtype=float)
    n = scores.size
    if n == 0:
        raise ValueError("scores must be non-empty")
    # Finite-sample split-conformal quantile: ceil((n+1)*(1-alpha))/n empirical quantile.
    k = int(np.ceil((n + 1) * (1.0 - alpha)))
    k = min(max(k, 1), n)
    return float(np.partition(scores, k - 1)[k - 1])


class SplitConformalRidge:
    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self.model = Ridge(alpha=1.0)
        self.qhat: float | None = None
        self.cal_scores: np.ndarray | None = None

    def fit(self, X_train, y_train, X_cal, y_cal):
        self.model.fit(X_train, y_train)
        pred_cal = self.model.predict(X_cal)
        self.cal_scores = np.abs(y_cal - pred_cal)
        self.qhat = conformal_quantile(self.cal_scores, self.alpha)
        return self

    def predict_interval(self, X):
        if self.qhat is None:
            raise RuntimeError("fit must be called first")
        pred = self.model.predict(X)
        return pred - self.qhat, pred + self.qhat


class OracleWeightedSplitConformalRidge(SplitConformalRidge):
    """Weighted split CP using exact covariate density ratios supplied at prediction time."""

    def predict_interval_weighted(self, X, cal_weights: np.ndarray, test_weights: np.ndarray):
        if self.cal_scores is None:
            raise RuntimeError("fit must be called first")
        scores = np.asarray(self.cal_scores)
        cal_weights = np.asarray(cal_weights, dtype=float)
        test_weights = np.asarray(test_weights, dtype=float)
        if scores.shape[0] != cal_weights.shape[0]:
            raise ValueError("cal_weights length mismatch")

        order = np.argsort(scores)
        s = scores[order]
        w = cal_weights[order]
        cw = np.cumsum(w)
        total_cal = float(cw[-1])
        target_mass = (1.0 - self.alpha) * (total_cal + test_weights)

        # The weighted conformal distribution includes the test point at +infinity.
        # If target_mass exceeds calibration mass, the interval is infinite.
        idx = np.searchsorted(cw, target_mass, side="left")
        q = np.full(test_weights.shape, np.inf, dtype=float)
        finite = idx < s.size
        q[finite] = s[idx[finite]]

        pred = self.model.predict(X)
        return pred - q, pred + q


class ConformalizedQuantileRegressor:
    def __init__(self, alpha: float = 0.1, n_estimators: int = 80, random_state: int = 0):
        self.alpha = alpha
        lo = alpha / 2.0
        hi = 1.0 - alpha / 2.0
        self.lower_model = GradientBoostingRegressor(
            loss="quantile", alpha=lo, n_estimators=n_estimators, random_state=random_state
        )
        self.upper_model = GradientBoostingRegressor(
            loss="quantile", alpha=hi, n_estimators=n_estimators, random_state=random_state + 1
        )
        self.qhat: float | None = None

    def fit(self, X_train, y_train, X_cal, y_cal):
        self.lower_model.fit(X_train, y_train)
        self.upper_model.fit(X_train, y_train)
        lo = self.lower_model.predict(X_cal)
        hi = self.upper_model.predict(X_cal)
        scores = np.maximum(lo - y_cal, y_cal - hi)
        self.qhat = conformal_quantile(scores, self.alpha)
        return self

    def predict_interval(self, X):
        if self.qhat is None:
            raise RuntimeError("fit must be called first")
        lo = self.lower_model.predict(X) - self.qhat
        hi = self.upper_model.predict(X) + self.qhat
        return lo, hi
