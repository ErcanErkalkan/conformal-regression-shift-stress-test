from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


class ClassifierDensityRatio:
    """Regularized classifier estimate of q(x)/p(x), configurable and pre-lockable."""

    def __init__(self, max_iter: int = 500, random_state: int = 0, degree: int = 2, C: float = 0.01):
        if degree < 1:
            raise ValueError("degree must be >= 1")
        steps = []
        if degree > 1:
            steps.append(("poly", PolynomialFeatures(degree=degree, include_bias=False)))
        steps.extend([
            ("scale", StandardScaler()),
            ("logit", LogisticRegression(C=float(C), max_iter=max(200, max_iter), solver="lbfgs", random_state=random_state)),
        ])
        self.model = Pipeline(steps)
        self.prior_ratio = 1.0
        self.degree = degree
        self.C = float(C)

    def fit(self, X_source: np.ndarray, X_target: np.ndarray):
        X = np.vstack([X_source, X_target])
        y = np.concatenate([np.zeros(len(X_source), dtype=int), np.ones(len(X_target), dtype=int)])
        self.model.fit(X, y)
        self.prior_ratio = float(len(X_source) / len(X_target))
        return self

    def ratio(self, X: np.ndarray) -> np.ndarray:
        p_target = self.model.predict_proba(X)[:, 1]
        p_target = np.clip(p_target, 1e-5, 1.0 - 1e-5)
        return self.prior_ratio * p_target / (1.0 - p_target)

    def heldout_auc(self, X_source: np.ndarray, X_target: np.ndarray) -> float:
        X = np.vstack([X_source, X_target])
        y = np.concatenate([np.zeros(len(X_source), dtype=int), np.ones(len(X_target), dtype=int)])
        score = self.model.predict_proba(X)[:, 1]
        return float(roc_auc_score(y, score))
