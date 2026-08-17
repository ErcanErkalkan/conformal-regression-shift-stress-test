from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

@dataclass
class DensityRatioModel:
    pipeline: Pipeline
    C: float
    prior_ratio: float

    def probabilities(self, X):
        return self.pipeline.predict_proba(np.asarray(X, float))[:, 1]

    def ratio(self, X):
        """Estimate q(x)/p(x) using one globally consistent classifier-odds scale.

        With source label 0, target label 1,
        q/p = [P(D=1|x)/P(D=0|x)] * [pi_source/pi_target].
        No batch-specific normalization is permitted because calibration and test
        weights must remain on the same relative scale in weighted conformal CP.
        """
        p = np.clip(self.probabilities(X), 1e-8, 1 - 1e-8)
        odds = p / (1 - p)
        return self.prior_ratio * odds


def fit_density_ratio(X_source_fit, X_target_unlabeled, C=0.1):
    Xs = np.asarray(X_source_fit, float); Xt = np.asarray(X_target_unlabeled, float)
    if len(Xs) != len(Xt):
        raise ValueError("Prelock protocol requires balanced source/target domain fitting")
    X = np.vstack([Xs, Xt])
    y = np.r_[np.zeros(len(Xs), dtype=int), np.ones(len(Xt), dtype=int)]
    pipe = Pipeline([
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(C=float(C), max_iter=1000, solver="lbfgs")),
    ])
    pipe.fit(X, y)
    prior_ratio = float(len(Xs) / len(Xt))
    return DensityRatioModel(pipe, float(C), prior_ratio)


def heldout_domain_auc(model: DensityRatioModel, X_source_holdout, X_target_holdout):
    ps = model.probabilities(X_source_holdout)
    pt = model.probabilities(X_target_holdout)
    y = np.r_[np.zeros(len(ps), dtype=int), np.ones(len(pt), dtype=int)]
    return float(roc_auc_score(y, np.r_[ps, pt]))
