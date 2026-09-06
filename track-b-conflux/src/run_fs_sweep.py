#!/usr/bin/env python3
"""Track B kill test: does a guard's latency advantage buy first-segment ownership?

Runs the paper's FS detector across the open latency-advantage datasets and
writes results/fs-sweep.json. Closed data is not needed: every file used here is
openly downloadable and sha512-verified (track-a-robustness/logs/deltas.md).
"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "track-a-robustness", "src"))
import data                     # noqa: E402  (Track A loader, same .npz layout)
from fs_detector import is_fs   # noqa: E402

# Guard latency advantage in ms -> file. 0 ms is the unmanipulated Conflux
# collection; the rest add delay to the client's other guards (thesis 4.3.1).
SWEEP = [
    (0,   "post-conflux/post-month2-cfx2-ca.npz"),
    (32,  "post-conflux/post-month2-cfx2-ca-rtt-032.npz"),
    (64,  "post-conflux/post-month2-cfx2-ca-rtt-064.npz"),
    (128, "post-conflux/post-month2-cfx2-ca-rtt-128.npz"),
    (256, "post-conflux/post-month2-cfx2-ca-rtt-256.npz"),
    (512, "post-conflux/post-month2-cfx2-ca-rtt-512.npz"),
]

# Controls. cfx0 has one leg per load, so a correct detector must call almost
# all of it FS. Other cfx2 sites check that 0 ms is not a CA peculiarity.
CONTROLS = [
    ("cfx0 CA month0", "post-conflux/post-month0-cfx0-ca.npz"),
    ("cfx0 UK month2", "post-conflux/post-month2-cfx0-uk.npz"),
    ("cfx2 AU month2", "post-conflux/post-month2-cfx2-au.npz"),
    ("cfx2 UK month2", "post-conflux/post-month2-cfx2-uk.npz"),
]

OFFSETS = [0, 1, 2, 3, 4]   # sensitivity to where the handshake is assumed to end


def measure(relpath):
    X, T, y = data.load(relpath)
    cells = (X != 0).sum(1)
    fs = is_fs(X)
    row = {
        "file": relpath, "n": int(len(y)),
        "fs_rate": float(fs.mean()),
        "n_fs": int(fs.sum()),
        "median_cells": float(np.median(cells)),
        "median_cells_fs": float(np.median(cells[fs])) if fs.any() else None,
        "median_cells_nonfs": float(np.median(cells[~fs])) if (~fs).any() else None,
        "median_duration_s": float(np.median(T.max(1))),
        "fs_rate_by_offset": {str(o): float(is_fs(X, offset=o).mean()) for o in OFFSETS},
    }
    return row


def main():
    out = {"sweep": [], "controls": []}
    print("advantage  n        FS rate   median cells (all / FS / non-FS)")
    for ms, f in SWEEP:
        r = measure(f); r["advantage_ms"] = ms
        out["sweep"].append(r)
        print(f"{ms:>6} ms  {r['n']:>7,}  {r['fs_rate']:.4f}    "
              f"{r['median_cells']:.0f} / {r['median_cells_fs']:.0f} / {r['median_cells_nonfs']:.0f}")
    print("\ncontrols")
    for name, f in CONTROLS:
        r = measure(f); r["name"] = name
        out["controls"].append(r)
        print(f"  {name:16s} n={r['n']:>7,}  FS rate {r['fs_rate']:.4f}  median cells {r['median_cells']:.0f}")

    dest = os.path.join(ROOT, "results", "fs-sweep.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
