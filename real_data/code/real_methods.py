from __future__ import annotations
import numpy as np
from sklearn.preprocessing import StandardScaler
from conformal_core import SplitConformalRidge, OracleWeightedSplitConformalRidge, ConformalizedQuantileRegressor

class ScaledRealMethods:
    """Locked model preprocessing for one real-data repetition."""
    def __init__(self, alpha=0.1, cqr_estimators=80, random_state=0):
        self.alpha=float(alpha)
        self.x_scaler=StandardScaler()
        self.y_mean=None; self.y_sd=None
        self.scp=SplitConformalRidge(alpha=self.alpha)
        self.wcp=OracleWeightedSplitConformalRidge(alpha=self.alpha)
        self.cqr=ConformalizedQuantileRegressor(alpha=self.alpha,n_estimators=int(cqr_estimators),random_state=int(random_state))

    def fit(self,Xtr,ytr,Xcal,ycal):
        Xtr_s=self.x_scaler.fit_transform(np.asarray(Xtr,float))
        Xcal_s=self.x_scaler.transform(np.asarray(Xcal,float))
        ytr=np.asarray(ytr,float); ycal=np.asarray(ycal,float)
        self.y_mean=float(ytr.mean()); self.y_sd=float(ytr.std(ddof=0))
        if not np.isfinite(self.y_sd) or self.y_sd<=1e-12:
            raise ValueError("target variance too small")
        ytr_s=(ytr-self.y_mean)/self.y_sd; ycal_s=(ycal-self.y_mean)/self.y_sd
        self.scp.fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
        self.wcp.fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
        self.cqr.fit(Xtr_s,ytr_s,Xcal_s,ycal_s)
        return self

    def xy_test(self,X,y):
        Xs=self.x_scaler.transform(np.asarray(X,float))
        ys=(np.asarray(y,float)-self.y_mean)/self.y_sd
        return Xs,ys
