#!/usr/bin/env python3
"""Precompute the RF TAM cache for the five axis collections.

Caches at the published 1800 slots. Appendix C.1's coarser settings (300 and
150 slots, i.e. 150 ms and 300 ms) are exact aggregations of it, so one cache
covers the whole slot-size sweep. Written to data/cache/, which is gitignored.
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
