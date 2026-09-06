#!/usr/bin/env python3
"""SUPERSEDED, and currently non-functional. Kept for history, do not run.

This was written against the CPU-prep `models.py`, whose API (`TAM_LEN`, `tam`,
`tam_downsample`) no longer exists, so importing it raises AttributeError.

Two reasons it was not ported:

1. It is unnecessary. Building the TAM for a whole collection takes about 5 s
   on the GPU box, so `run_torch.py rf` just builds it, once per collection per
   run, and never touches disk.
2. Its central shortcut is invalid under the corrected binning. The authors'
   released code bins with `idx = int(t*(N-1)/Tmax)`, so a slot is Tmax/(N-1),
   not Tmax/N. Under that formula the 1800-slot matrix does not partition
   evenly into 300 or 150 slots, so `tam_downsample` is not the exact
   aggregation it claims to be, and the slot-size sweep genuinely does need a
   rebuild per setting. `run_torch.py --slots` does exactly that.

See logs/deltas.md, row "TAM Tmax and binning".
"""
import os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, models

CACHE = os.path.join(data.ROOT, "data", "cache")
FILES = [
    "pre-conflux/pre-month0-cfx0-au.npz",
    "pre-conflux/pre-month0-cfx0-ca.npz",
    "post-conflux/post-month0-cfx0-uk.npz",
    "post-conflux/post-month2-cfx0-uk.npz",
    "post-conflux/post-month6-cfx0-uk.npz",
]


def cache_path(relpath, n_slots=models.TAM_LEN):
    name = os.path.basename(relpath).replace(".npz", "")
    return os.path.join(CACHE, f"tam-{n_slots}-{name}.npy")


def load_or_build(relpath, n_slots=models.TAM_LEN, verbose=True):
    """Return the (n, 2, n_slots) TAM, from cache when possible."""
    fine = cache_path(relpath)
    if os.path.exists(fine):
        arr = np.load(fine, mmap_mode="r")
        return models.tam_downsample(np.asarray(arr), n_slots)
    X, T, _ = data.load(relpath)
    t0 = time.time()
    arr = models.tam(X, T)
    os.makedirs(CACHE, exist_ok=True)
    np.save(fine, arr)
    if verbose:
        print(f"  built {os.path.basename(fine)} {arr.shape} "
              f"{arr.nbytes / 1e6:.0f} MB in {time.time() - t0:.0f}s")
    return models.tam_downsample(arr, n_slots)


def main():
    os.makedirs(CACHE, exist_ok=True)
    for f in FILES:
        if os.path.exists(cache_path(f)):
            print(f"[have] {os.path.basename(cache_path(f))}")
            continue
        print(f"[build] {f}")
        load_or_build(f)
    total = sum(os.path.getsize(os.path.join(CACHE, x)) for x in os.listdir(CACHE))
    print(f"\ncache total {total / 1e9:.2f} GB in {CACHE}")


if __name__ == "__main__":
    main()
