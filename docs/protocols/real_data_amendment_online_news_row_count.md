Real-Data Amendment v0.3.1 — Online News Popularity Row Count

Issue  
The prelocked manifest specified expected\_rows \= 39797 for UCI dataset 332 (Online News Popularity), matching the current UCI metadata page. During local Windows acquisition with ucimlrepo==0.0.7, fetch\_ucirepo(id=332) reported metadata.num\_instances \= 39797 but returned data.original.shape \= (39644, 61), data.features.shape \= (39644, 58), and data.targets.shape \= (39644, 1).

Decision  
For the executable benchmark, the usable canonical row count is locked to 39644\. This amendment changes only online\_news.expected\_rows from 39797 to 39644\. Dataset identity, UCI ID 332, DOI 10.24432/C5NS3V, target 'shares', dropped columns \['url','timedelta'\], split fractions, target sizes, lambda grid, estimators, repetitions, seeds, thresholds, and methods remain unchanged.

Rationale  
The row-count guardrail must validate the data matrix actually returned by the official UCI Python import path rather than a conflicting metadata field. The discrepancy is documented rather than silently bypassed. No rows are manually deleted or imputed and no unofficial mirror is substituted.

Local evidence recorded on 2026-08-17  
metadata: 39797  
original: (39644, 61\)  
features: (39644, 58\)  
targets: (39644, 1\)

Implementation  
Create an amended local manifest and rerun acquisition/validation. Preserve the original prelock manifest unchanged for auditability.

Status  
AMENDMENT APPROVED BEFORE COMPARATIVE REAL-DATA RESULTS.  
