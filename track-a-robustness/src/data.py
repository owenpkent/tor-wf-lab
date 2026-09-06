"""Loading and split construction for the OSF monitored traces.

File contents (verified 2026-09-06): each .npz holds
  X (n, 5000) int64  direction sequence, +1 out / -1 in, 0 pad
  T (n, 5000) float64 arrival timestamps in seconds, 0 pad
  y (n,)      int64  site label, nominal space 0..111

Everything here is closed-world. The paper's tables are open-world against the
DUA-gated background set, so nothing produced from these splits is numerically
comparable to Table 4.1 / 4.3. See logs/osf-inventory.md.
"""
import os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Axis definitions, matched to the thesis rather than to the brief's shorthand.
#   Cross-network  = thesis Table 4.1, pre-Conflux dataset, train AU / test CA.
#   Concept drift  = thesis Table 4.3, UK client, train month 0 / test month 2, 6.
CROSS_NETWORK = {
    "train": "pre-conflux/pre-month0-cfx0-au.npz",
    "test":  {"ca": "pre-conflux/pre-month0-cfx0-ca.npz"},
}
DRIFT = {
    "train": "post-conflux/post-month0-cfx0-uk.npz",
    "test":  {"month2": "post-conflux/post-month2-cfx0-uk.npz",
              "month6": "post-conflux/post-month6-cfx0-uk.npz"},
}

# The thesis reports exactly one network pair, AU -> CA on the pre-Conflux
# dataset, so a classifier's "network-mismatch robustness" is measured at a
# single point. Post-Conflux month 0 is the only collection where AU, CA and UK
# were gathered together, which makes it the only place to ask whether that
# result is a property of the representation or of that one pair. These two axes
# are a different dataset from CROSS_NETWORK and are not comparable to it cell
# for cell; the comparison that matters is between the cells *within* each axis.
CROSS_NETWORK_POST_AU = {
    "train": "post-conflux/post-month0-cfx0-au.npz",
    "test":  {"ca": "post-conflux/post-month0-cfx0-ca.npz",
              "uk": "post-conflux/post-month0-cfx0-uk.npz"},
}
CROSS_NETWORK_POST_UK = {
    "train": "post-conflux/post-month0-cfx0-uk.npz",
    "test":  {"au": "post-conflux/post-month0-cfx0-au.npz",
              "ca": "post-conflux/post-month0-cfx0-ca.npz"},
}

AXES = {
    "cross-network": CROSS_NETWORK,
    "drift": DRIFT,
    "cross-network-post-au": CROSS_NETWORK_POST_AU,
    "cross-network-post-uk": CROSS_NETWORK_POST_UK,
}


def load(relpath, downcast=True):
    """X int8, T float32, y int16. Full precision is not needed and the int64
    originals are 837 MB per array."""
    z = np.load(os.path.join(DATA, relpath))
    X, T, y = z["X"], z["T"], z["y"]
    if downcast:
        X, T, y = X.astype(np.int8), T.astype(np.float32), y.astype(np.int16)
    return X, T, y


def common_labels(*label_arrays, min_count=1):
    """Labels present in every split with at least min_count traces.

    Sites disappear between collections (six of them are gone from the UK
    month-6 set), so a fixed 0..111 label space would score a classifier on
    classes that cannot occur in the test set.
    """
    keep = None
    for y in label_arrays:
        u, c = np.unique(y, return_counts=True)
        s = set(u[c >= min_count].tolist())
        keep = s if keep is None else (keep & s)
    return np.array(sorted(keep), dtype=np.int16)


def restrict(X, T, y, labels):
    m = np.isin(y, labels)
    return X[m], T[m], y[m]


def relabel(y, labels):
    """Map the surviving site ids onto 0..k-1 for the classifiers."""
    lut = {int(l): i for i, l in enumerate(labels)}
    return np.array([lut[int(v)] for v in y], dtype=np.int16)


def axis_split(axis, min_count=1, verbose=True):
    """Return (Xtr, Ttr, ytr), {name: (Xte, Tte, yte)}, labels.

    Label space is the intersection over the training set and every test set of
    that axis, so all cells of one axis are scored on the same classes.
    """
    spec = AXES[axis]
    tr = load(spec["train"])
    tes = {k: load(v) for k, v in spec["test"].items()}
    labels = common_labels(tr[2], *[t[2] for t in tes.values()], min_count=min_count)
    Xtr, Ttr, ytr = restrict(*tr, labels)
    out = {}
    for k, t in tes.items():
        Xte, Tte, yte = restrict(*t, labels)
        out[k] = (Xte, Tte, relabel(yte, labels))
    if verbose:
        print(f"[{axis}] {len(labels)} common classes (min_count={min_count})")
        print(f"  train {spec['train']}: {len(ytr):,} traces")
        for k, v in spec["test"].items():
            print(f"  test  {k} {v}: {len(out[k][2]):,} traces")
    return (Xtr, Ttr, relabel(ytr, labels)), out, labels
