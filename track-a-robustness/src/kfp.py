"""k-FP (Hayes & Danezis 2016) closed-world, on the OSF monitored traces.

Reimplementation, not the authors' code: nothing was released (see
logs/osf-inventory.md). Hyperparameters follow thesis Table C.1 (the brief's
"Appendix A Table 7"): Random Forest, n_estimators = 1000, feature vector of
175 dimensions. Every judgement call the table does not pin down is listed in
logs/deltas.md.

Closed-world only. The paper's k-FP numbers are open-world pi_10 / recall
against the DUA-gated background set and are not comparable to these.
"""
import numpy as np

N_FEATURES = 175
CHUNK = 20          # outgoing-packet concentration chunk size, per the paper
N_CHUNKS = 40       # raw concentration values kept
N_SECONDS = 40      # raw packets-per-second bins kept
N_ALT_CONC = 20     # alternative concentration buckets
N_CUMUL = 20        # cumulative-direction sample points


def _stats(a, empty=0.0):
    if a.size == 0:
        return np.array([empty] * 4, dtype=np.float32)
    return np.array([a.max(), a.mean(), a.std(), np.percentile(a, 75)], dtype=np.float32)


def _pcts(a, empty=0.0):
    if a.size == 0:
        return np.array([empty] * 4, dtype=np.float32)
    return np.array([np.percentile(a, p) for p in (25, 50, 75, 100)], dtype=np.float32)


def _bursts(dirs):
    """Lengths of consecutive runs of outgoing packets."""
    if dirs.size == 0:
        return np.zeros(0, dtype=np.float32)
    out = dirs > 0
    edges = np.diff(np.concatenate(([0], out.view(np.int8), [0])))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return (ends - starts).astype(np.float32)


def features_one(dirs, times):
    """175-dimensional k-FP-style feature vector for a single trace."""
    f = []
    n = dirs.size
    out_m, in_m = dirs > 0, dirs < 0
    n_out, n_in = int(out_m.sum()), int(in_m.sum())

    # A. counts (5)
    f += [n, n_out, n_in, n_out / n if n else 0.0, n_in / n if n else 0.0]

    # B. inter-arrival time stats, total / out / in (12)
    for m in (slice(None), out_m, in_m):
        t = times[m]
        f += list(_stats(np.diff(t) if t.size > 1 else np.zeros(0, np.float32)))

    # C. transmission-time percentiles, total / out / in (12)
    for m in (slice(None), out_m, in_m):
        f += list(_pcts(times[m]))

    # D. first 30 / last 30 composition (4)
    head, tail = dirs[:30], dirs[-30:]
    f += [int((head > 0).sum()), int((head < 0).sum()),
          int((tail > 0).sum()), int((tail < 0).sum())]

    # concentration of outgoing packets in chunks of CHUNK
    pad = (-n) % CHUNK
    chunks = np.concatenate([out_m, np.zeros(pad, bool)]).reshape(-1, CHUNK).sum(1).astype(np.float32)

    # E. concentration stats (6)
    if chunks.size:
        f += [chunks.std(), chunks.mean(), np.percentile(chunks, 50),
              chunks.min(), chunks.max(), chunks.sum()]
    else:
        f += [0.0] * 6

    # packets per second
    dur = float(times[-1]) if n else 0.0
    nbins = max(int(np.ceil(dur)), 1)
    persec = np.bincount((times.astype(np.int32) if n else np.zeros(0, np.int32)),
                         minlength=nbins).astype(np.float32)

    # F. packets-per-second stats (5)
    if persec.size:
        f += [persec.mean(), persec.std(), np.percentile(persec, 50), persec.min(), persec.max()]
    else:
        f += [0.0] * 5

    # G. packet ordering: index positions of out / in packets (4)
    pos = np.arange(n, dtype=np.float32)
    for m in (out_m, in_m):
        p = pos[m]
        f += [p.mean() if p.size else 0.0, p.std() if p.size else 0.0]

    # H. outgoing burst stats (7)
    b = _bursts(dirs)
    f += [b.max() if b.size else 0.0, b.mean() if b.size else 0.0, float(b.size),
          float((b > 5).sum()), float((b > 10).sum()), float((b > 15).sum()),
          float((b > 20).sum())]

    # I. first N_CHUNKS raw concentration values (40)
    f += list(np.resize(np.pad(chunks, (0, max(0, N_CHUNKS - chunks.size)))[:N_CHUNKS], N_CHUNKS))

    # J. first N_SECONDS raw per-second counts (40)
    f += list(np.pad(persec, (0, max(0, N_SECONDS - persec.size)))[:N_SECONDS])

    # K. alternative concentration: chunk list summed into N_ALT_CONC buckets (20)
    if chunks.size:
        idx = np.minimum((np.arange(chunks.size) * N_ALT_CONC) // chunks.size, N_ALT_CONC - 1)
        f += list(np.bincount(idx, weights=chunks, minlength=N_ALT_CONC)[:N_ALT_CONC])
    else:
        f += [0.0] * N_ALT_CONC

    # L. cumulative direction sampled at N_CUMUL points (20)
    if n:
        cum = np.cumsum(dirs.astype(np.float32))
        f += list(cum[np.linspace(0, n - 1, N_CUMUL).astype(int)])
    else:
        f += [0.0] * N_CUMUL

    v = np.asarray(f, dtype=np.float32)
    assert v.size == N_FEATURES, f"{v.size} features, expected {N_FEATURES}"
    return v


def _block(Xb, Tb):
    return np.stack([features_one(Xb[i][Xb[i] != 0], Tb[i][Xb[i] != 0])
                     for i in range(Xb.shape[0])])


def featurize(X, T, n_jobs=-1, chunk=1024):
    """Feature matrix for a whole collection.

    Slices are passed as arguments rather than captured in a closure: joblib
    memmaps large array arguments, whereas a closure over the full X and T
    cloudpickles all 500 MB of them to every worker.
    """
    from joblib import Parallel, delayed

    n = X.shape[0]
    parts = Parallel(n_jobs=n_jobs, prefer="processes")(
        delayed(_block)(X[lo:lo + chunk], T[lo:lo + chunk])
        for lo in range(0, n, chunk))
    return np.concatenate(parts)
