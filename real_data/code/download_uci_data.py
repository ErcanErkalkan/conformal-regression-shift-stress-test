from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def find_column(columns, requested, aliases=()):
    lookup = {str(c).strip().lower(): c for c in columns}
    for name in (requested, *aliases):
        key = str(name).strip().lower()
        if key in lookup:
            return lookup[key]
    raise KeyError(f"Target {requested!r} not found; columns={list(columns)}")


def canonicalize(df: pd.DataFrame, spec: dict):
    df = clean_columns(df)
    target_col = find_column(df.columns, spec["target"], spec.get("target_aliases", []))
    drops_lower = {str(x).lower() for x in spec.get("drop_columns", [])}
    feature_cols = [c for c in df.columns if c != target_col and str(c).lower() not in drops_lower]
    if "allowed_predictors" in spec:
        allowed = {x.lower() for x in spec["allowed_predictors"]}
        feature_cols = [c for c in feature_cols if str(c).lower() in allowed]
    X = df[feature_cols].apply(pd.to_numeric, errors="raise")
    y = pd.to_numeric(df[target_col], errors="raise").rename("target")
    out = pd.concat([X, y], axis=1)
    return out, feature_cols, str(target_col)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="configs/dataset_manifest.json")
    parser.add_argument("--out", default="data/canonical")
    args = parser.parse_args()
    try:
        from ucimlrepo import fetch_ucirepo
    except ImportError as e:
        raise SystemExit("Install pinned dependency: pip install ucimlrepo==0.0.7") from e

    manifest = json.loads(Path(args.manifest).read_text())
    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in manifest["datasets"]:
        ds = fetch_ucirepo(id=int(spec["uci_id"]))
        original = ds.data.original
        if original is None:
            original = pd.concat([ds.data.features, ds.data.targets], axis=1)
        canonical, feature_cols, actual_target = canonicalize(original, spec)
        if len(canonical) != int(spec["expected_rows"]):
            raise RuntimeError(f"{spec['key']}: expected {spec['expected_rows']} rows, got {len(canonical)}")
        if canonical.isna().any().any():
            na_rate = float(canonical.isna().any(axis=1).mean())
            raise RuntimeError(f"{spec['key']}: unexpected missing rows rate={na_rate:.6f}; amend protocol before removal")
        path = outdir / f"{spec['key']}.csv"
        canonical.to_csv(path, index=False)
        records.append({
            "key": spec["key"], "uci_id": spec["uci_id"], "doi": spec["doi"],
            "rows": len(canonical), "predictor_count": len(feature_cols),
            "predictors": feature_cols, "target_original": actual_target,
            "canonical_target": "target", "sha256": sha256_file(path),
            "canonical_file": str(path)
        })
        print(spec["key"], len(canonical), len(feature_cols), records[-1]["sha256"])
    Path(outdir / "dataset_manifest.json").write_text(json.dumps(records, indent=2))

if __name__ == "__main__":
    main()
