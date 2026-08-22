from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# The locked public modules live under real_data/code in the GitHub release.
sys.path.insert(0, str(REPO / "real_data" / "code"))
sys.path.insert(0, str(HERE))

import run_p03_density_estimators as p

ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()

if args.smoke:
    syn = p.run_synthetic(rep_start=0, rep_end=1)
    pub = p.run_public(rep_start=0, rep_end=1, datasets=["ccpp"])
else:
    syn = p.run_synthetic()
    pub = p.run_public()

p.summarize(syn, pub)
