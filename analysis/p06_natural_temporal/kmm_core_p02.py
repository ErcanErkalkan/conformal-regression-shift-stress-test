from __future__ import annotations
import math
import numpy as np
from scipy.spatial.distance import cdist, pdist

B = 30.0
BAND_FACTORS = np.array([0.01, 0.1, 0.5, 1.0, 2.0], float)

def project_capped_simplex(v: np.ndarray, total: float, upper: float) -> np.ndarray:
    v=np.asarray(v,float)
    if total < 0 or total > upper*len(v): raise ValueError('infeasible projection')
    lo=float(np.min(v-upper))-1.0; hi=float(np.max(v))+1.0
    for _ in range(70):
        mid=(lo+hi)/2; s=np.clip(v-mid,0,upper).sum()
        if s>total: lo=mid
        else: hi=mid
    w=np.clip(v-(lo+hi)/2,0,upper)
    err=total-w.sum()
    if abs(err)>1e-8:
        free=np.where((w>1e-10)&(w<upper-1e-10))[0]
        if len(free): w[free]+=err/len(free)
    return np.clip(w,0,upper)

def power_lmax(K: np.ndarray, iters=35) -> float:
    n=len(K); x=np.ones(n)/math.sqrt(n)
    for _ in range(iters):
        y=K@x; ny=np.linalg.norm(y)
        if ny<=1e-14: return 1.0
        x=y/ny
    return max(float(x@(K@x)),1e-8)

def kmm_solve(Xs, Xt, sigma, B=B, max_iter=250, tol=1e-4):
    Xs=np.asarray(Xs,float); Xt=np.asarray(Xt,float); n=len(Xs); m=len(Xt)
    gamma=1.0/(2*sigma*sigma)
    K=np.exp(-gamma*cdist(Xs,Xs,'sqeuclidean')); K.flat[::n+1]+=1e-9
    Kst=np.exp(-gamma*cdist(Xs,Xt,'sqeuclidean')); kappa=(n/m)*Kst.sum(axis=1)
    L=power_lmax(K); w=np.ones(n); y=w.copy(); tk=1.0; pg=np.inf
    for it in range(max_iter):
        grad=K@y-kappa; wn=project_capped_simplex(y-grad/L,float(n),float(B))
        tnew=(1+math.sqrt(1+4*tk*tk))/2; y=wn+((tk-1)/tnew)*(wn-w)
        if it%25==0 or it==max_iter-1:
            g=K@wn-kappa; proj=project_capped_simplex(wn-g/L,float(n),float(B))
            pg=float(np.linalg.norm(wn-proj)/max(1.0,np.linalg.norm(wn)))
            if pg<tol: w=wn; break
        w=wn; tk=tnew
    obj=float(0.5*w@(K@w)-kappa@w)
    return w, {'iterations':it+1,'pg_residual':pg,'objective':obj,'lmax':L}

def mmd_unbiased_from_kernel(K,n):
    m=K.shape[0]-n; Kxx=K[:n,:n]; Kyy=K[n:,n:]; Kxy=K[:n,n:]
    a=(Kxx.sum()-np.trace(Kxx))/(n*(n-1)) if n>1 else 0
    b=(Kyy.sum()-np.trace(Kyy))/(m*(m-1)) if m>1 else 0
    c=Kxy.mean(); return float(a+b-2*c)

def select_sigma(Xs,Xt,seed,max_each=120,n_perm=12):
    rng=np.random.default_rng(seed)
    isrc=np.linspace(0,len(Xs)-1,min(max_each,len(Xs)),dtype=int)
    itgt=np.linspace(0,len(Xt)-1,min(max_each,len(Xt)),dtype=int)
    A=np.asarray(Xs)[isrc]; Bx=np.asarray(Xt)[itgt]; Z=np.vstack([A,Bx]); n=len(A); N=len(Z)
    dist=pdist(Z,'euclidean'); pos=dist[dist>1e-12]; med=float(np.median(pos)) if len(pos) else 1.0
    perm_indices=[rng.permutation(N) for _ in range(n_perm)]; rows=[]
    for f in BAND_FACTORS:
        sig=max(float(f*med),1e-8); K=np.exp(-cdist(Z,Z,'sqeuclidean')/(2*sig*sig)); obs=mmd_unbiased_from_kernel(K,n)
        vals=[mmd_unbiased_from_kernel(K[np.ix_(p,p)],n) for p in perm_indices]
        mu=float(np.mean(vals)); sd=float(np.std(vals,ddof=1)) if len(vals)>1 else 0; z=(obs-mu)/sd if sd>1e-10 else -np.inf
        rows.append((z,-abs(math.log10(f)) if f>0 else -99,sig,float(f),obs))
    best=max(rows,key=lambda x:(x[0],x[1]))
    return best[2], {'factor':best[3],'median_distance':med,'standardized_mmd':best[0],'mmd_unbiased':best[4]}

def weighted_quantile(scores,weights,q=0.9):
    scores=np.asarray(scores,float); weights=np.asarray(weights,float); w=weights/weights.sum(); order=np.argsort(scores); s=scores[order]; cw=np.cumsum(w[order])
    j=int(np.searchsorted(cw,q,side='left')); return float(s[min(j,len(s)-1)])
