#!/usr/bin/env python3
"""Is a first-segment trace actually more classifiable, and by how much?

The kill test (notes/06) measured how often a latency-advantaged guard owns the
first segment. It could not measure what owning it is worth: that number was
inferred from the paper's TPR under the assumption that non-first-segment traces
contribute nothing. This measures it instead.

Design: for each latency setting, train k-FP on a stratified 80% of that
collection, mixed FS and non-FS exactly as an attacker would collect it, then
score the held-out 20% separately on its FS and non-FS traces.

  P(correct | FS) and P(correct | non-FS), per latency advantage, 3 seeds.

Closed world, so these are not the paper's open-world TPRs and the absolute
levels will be far higher. The quantity of interest is the ratio and its trend.
"""
import json, os, sys, time
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "track-a-robustness", "src"))
import data, kfp                       # noqa: E402
from fs_detector import is_fs          # noqa: E402
from run_fs_sweep import SWEEP         # noqa: E402

N_ESTIMATORS = 1000                    # thesis Table C.1, as in Track A
SEEDS = [0, 1, 2]
HOLDOUT = 0.2
MIN_PER_CLASS = 20                     # need enough to survive the FS split


def common_labels():
    """Classes present with at least MIN_PER_CLASS traces in every condition, so
    the six latency settings are scored on one label space."""
    keep = None
    for _, f in SWEEP:
        _, _, y = data.load(f)
        u, c = np.unique(y, return_counts=True)
        s = set(u[c >= MIN_PER_CLASS].tolist())
        keep = s if keep is None else (keep & s)
    return np.array(sorted(keep), dtype=np.int16)


def main():
    labels = common_labels()
    print(f"{len(labels)} classes common to all six conditions "
          f"(>= {MIN_PER_CLASS} traces each)\n")
    rows = []
    for ms, f in SWEEP:
        X, T, y = data.load(f)
        m = np.isin(y, labels)
        X, T, y, fs = X[m], T[m], y[m], is_fs(X[m])
        t0 = time.time()
        F = kfp.featurize(X, T)
        print(f"{ms:>3} ms: n={len(y):,}  FS {fs.mean():.4f}  featurised {time.time()-t0:.0f}s")

        for seed in SEEDS:
            i_fit, i_hold = train_test_split(np.arange(len(y)), test_size=HOLDOUT,
                                             stratify=y, random_state=seed)
            clf = RandomForestClassifier(n_estimators=N_ESTIMATORS, n_jobs=-1,
                                         random_state=seed)
            clf.fit(F[i_fit], y[i_fit])
            pred = clf.predict(F[i_hold])
            yh, fh = y[i_hold], fs[i_hold]
            row = {"advantage_ms": ms, "seed": seed,
                   "n_train": int(len(i_fit)), "n_test": int(len(i_hold)),
                   "fs_rate_test": float(fh.mean()),
                   "acc_all": float(accuracy_score(yh, pred)),
                   "acc_fs": float(accuracy_score(yh[fh], pred[fh])) if fh.any() else None,
                   "acc_nonfs": float(accuracy_score(yh[~fh], pred[~fh])) if (~fh).any() else None,
                   "f1_macro_all": float(f1_score(yh, pred, average="macro")),
                   "median_cells_fs": float(np.median((X[i_hold][fh] != 0).sum(1))),
                   "median_cells_nonfs": float(np.median((X[i_hold][~fh] != 0).sum(1))),
                   "n_classes": int(len(labels))}
            rows.append(row)
            print(f"   seed {seed}: acc all {row['acc_all']:.4f}  "
                  f"FS {row['acc_fs']:.4f}  non-FS {row['acc_nonfs']:.4f}")

    dest = os.path.join(ROOT, "results", "fs-kfp.json")
    json.dump({"classifier": "k-FP", "world": "closed",
               "n_estimators": N_ESTIMATORS, "rows": rows}, open(dest, "w"), indent=1)
    print(f"\nwrote {dest}\n")

    print("summary, mean +/- sd over seeds")
    print(f"{'adv':>6} {'FS rate':>8} {'acc all':>16} {'acc | FS':>16} {'acc | non-FS':>16} {'ratio':>7}")
    for ms, _ in SWEEP:
        r = [x for x in rows if x["advantage_ms"] == ms]
        a = np.mean([x["acc_all"] for x in r]); sa = np.std([x["acc_all"] for x in r])
        f = np.mean([x["acc_fs"] for x in r]); sf = np.std([x["acc_fs"] for x in r])
        nf = np.mean([x["acc_nonfs"] for x in r]); snf = np.std([x["acc_nonfs"] for x in r])
        print(f"{ms:>4} ms {np.mean([x['fs_rate_test'] for x in r]):>8.4f} "
              f"{a:>9.4f}+/-{sa:.4f} {f:>9.4f}+/-{sf:.4f} {nf:>9.4f}+/-{snf:.4f} {f/nf:>7.2f}")


if __name__ == "__main__":
    main()
