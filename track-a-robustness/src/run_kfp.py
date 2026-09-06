#!/usr/bin/env python3
"""Run k-FP closed-world on both axes, 3+ seeds, write results/kfp.json.

Usage: python run_kfp.py [n_seeds]
"""
import json, os, sys, time
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, kfp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
N_ESTIMATORS = 1000          # thesis Table C.1
SEEDS = [0, 1, 2]
HOLDOUT = 0.2                # in-distribution anchor, stratified, per seed


def evaluate(axis, seeds, min_count=1):
    (Xtr, Ttr, ytr), tests, labels = data.axis_split(axis, min_count=min_count)
    t0 = time.time()
    Ftr = kfp.featurize(Xtr, Ttr)
    Fte = {k: kfp.featurize(v[0], v[1]) for k, v in tests.items()}
    print(f"  featurised in {time.time() - t0:.0f}s")

    rows = []
    for seed in seeds:
        # Hold out part of the training collection as the in-distribution
        # anchor. Without it a cross-network or month-6 score cannot be read as
        # degradation, only as an absolute number.
        Fa, Fh, ya, yh = train_test_split(Ftr, ytr, test_size=HOLDOUT,
                                          stratify=ytr, random_state=seed)
        clf = RandomForestClassifier(n_estimators=N_ESTIMATORS, n_jobs=-1,
                                     random_state=seed)
        t0 = time.time()
        clf.fit(Fa, ya)
        fit_s = time.time() - t0
        cells = {"in-dist": (Fh, yh)}
        cells.update({k: (F, tests[k][2]) for k, F in Fte.items()})
        for name, (F, yte) in cells.items():
            pred = clf.predict(F)
            rows.append({
                "axis": axis, "cell": name, "seed": seed,
                "accuracy": float(accuracy_score(yte, pred)),
                "f1_macro": float(f1_score(yte, pred, average="macro")),
                "f1_micro": float(f1_score(yte, pred, average="micro")),
                "n_train": int(len(ya)), "n_test": int(len(yte)),
                "n_classes": int(len(labels)), "fit_seconds": round(fit_s, 1),
            })
            print(f"  seed {seed} {axis}/{name}: acc={rows[-1]['accuracy']:.4f} "
                  f"macroF1={rows[-1]['f1_macro']:.4f} (fit {fit_s:.0f}s)")
    return rows


def main():
    seeds = list(range(int(sys.argv[1]))) if len(sys.argv) > 1 else SEEDS
    os.makedirs(RESULTS, exist_ok=True)
    rows = []
    for axis in ("cross-network", "drift"):
        print(f"== {axis} ==")
        rows += evaluate(axis, seeds)
    out = os.path.join(RESULTS, "kfp.json")
    json.dump({"classifier": "k-FP", "world": "closed",
               "n_estimators": N_ESTIMATORS, "rows": rows},
              open(out, "w"), indent=1)
    print(f"\nwrote {out}")

    print("\nsummary (mean +/- sd over seeds)")
    for axis in sorted({r["axis"] for r in rows}):
        for cell in sorted({r["cell"] for r in rows if r["axis"] == axis}):
            v = [r["f1_macro"] for r in rows if r["axis"] == axis and r["cell"] == cell]
            a = [r["accuracy"] for r in rows if r["axis"] == axis and r["cell"] == cell]
            print(f"  {axis:14s} {cell:8s} macroF1 {np.mean(v):.4f} +/- {np.std(v):.4f}"
                  f"   acc {np.mean(a):.4f} +/- {np.std(a):.4f}")


if __name__ == "__main__":
    main()
