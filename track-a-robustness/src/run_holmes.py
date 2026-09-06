#!/usr/bin/env python3
"""Holmes, the full four-stage pipeline, closed world, both axes, 3+ seeds.

Emits results/holmes.json with the same row schema as run_kfp.py and
run_torch.py so plot_axes.py can read all five classifiers.

Stages, following the authors' scripts/Holmes.sh exactly:
  A  auxiliary classifier (RF architecture) on the 1000-bin temporal feature,
     CrossEntropy / Adam 5e-4 / batch 200 / 30 epochs, best-F1 epoch kept
  B  DeepLiftShap attribution over that model, background = first 2 samples of
     every class, attributed = next 10 of the class being explained
  C  per-class effective range = the [30%, 60%] band of the cumulative
     attribution curve, then 2 truncated copies of every sample plus the
     original
  D  Holmes network on TAF only, SupConLoss(temperature 0.1) / AdamW 5e-4 /
     batch 256 / 30 epochs, best epoch by kNN monitor (k=10, t=0.1)
  then per-class centroid and MAD radius from the augmented validation set,
  and prediction by argmin(cosine distance - radius).

Usage: python run_holmes.py [--seeds 3] [--axes cross-network drift]
       python run_holmes.py --seeds 1 --axes cross-network --cells in-dist  # gate
"""
import argparse, json, os, sys, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, models, holmes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
DEV = "cuda" if torch.cuda.is_available() else "cpu"

HOLDOUT = 0.2            # in-distribution anchor, matches every other classifier
VALID_FRAC = 0.15        # carved from the training portion, see logs/deltas.md
NUM_AUG = 2              # data_augmentation.py, hardcoded
ATTR_LO, ATTR_HI = 0.3, 0.6
N_BG, N_ATTR = 2, 10   # background / attributed samples per class
STAGE_A = dict(epochs=30, batch=200, lr=5e-4)
STAGE_D = dict(epochs=30, batch=256, lr=5e-4, temperature=0.1, knn_k=10, knn_t=0.1)


# ------------------------------------------------------------------- stage A

def train_stage_a(Xf, yf, Xv, yv, n_classes, seed, log):
    """Auxiliary temporal classifier. Returns the best-F1 model, on CPU."""
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    net = models.RFNet(n_classes).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=STAGE_A["lr"])
    lossf = nn.CrossEntropyLoss()
    g = torch.Generator(device=DEV); g.manual_seed(seed)
    best_f1, best_state = -1.0, None
    for ep in range(STAGE_A["epochs"]):
        net.train()
        perm = torch.randperm(len(Xf), device=DEV, generator=g)
        for i in range(0, len(Xf), STAGE_A["batch"]):
            idx = perm[i:i + STAGE_A["batch"]]
            if len(idx) < 2:
                continue
            opt.zero_grad(set_to_none=True)
            lossf(net(Xf[idx]), yf[idx]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            pred = torch.cat([net(Xv[i:i + 512]).argmax(1).cpu()
                              for i in range(0, len(Xv), 512)]).numpy()
        f1 = f1_score(yv, pred, average="macro")
        if f1 > best_f1:
            best_f1, best_state = f1, {k: v.detach().clone()
                                       for k, v in net.state_dict().items()}
        if (ep + 1) % 10 == 0:
            log(f"    [A] epoch {ep+1:2d} valid macroF1 {f1:.4f} (best {best_f1:.4f})")
    net.load_state_dict(best_state)
    log(f"    [A] best valid macroF1 {best_f1:.4f}")
    return net, best_f1


# ------------------------------------------------------------------- stage B

def feature_attr(net, Xv, yv, n_classes, log, chunk=2):
    """DeepLiftShap, transcribed from WFlib analyzer.feature_attr.

    Background is the first 2 samples of every class concatenated; the samples
    explained are the next 10 of the target class. Attributions are summed over
    those samples and over the two direction rows, giving one 1000-long curve
    per class. Attribution runs in small chunks purely to bound activation
    memory; the sum is identical.
    """
    from captum import attr as cattr
    net.eval()
    bg, test, short = [], {}, []
    for c in range(n_classes):
        cur = Xv[yv == c]
        if len(cur) < N_BG + 1:
            raise RuntimeError(f"class {c} has {len(cur)} validation samples, "
                               f"attribution needs at least {N_BG + 1}")
        bg.append(cur[:N_BG])
        test[c] = cur[N_BG:N_BG + N_ATTR]        # up to N_ATTR, fewer if rare
        if len(test[c]) < N_ATTR:
            short.append((c, len(test[c])))
    bg = torch.cat(bg, dim=0)
    if short:
        # Their code asserts >= 12 per class. The drift axis has rarer classes
        # than theirs (one has 74 traces), so a fixed 15% validation split
        # cannot always supply 10. Attributing over fewer samples for those
        # classes is a far smaller deviation than enlarging the validation
        # split, which would have cost Holmes training data the other four
        # classifiers keep. See logs/deltas.md.
        log(f"    [B] {len(short)} class(es) below {N_ATTR} attributed samples, "
            f"fewest {min(n for _, n in short)}: {[c for c, _ in short][:8]}")
    dl = cattr.DeepLiftShap(net)
    out = []
    t0 = time.time()
    for c in range(n_classes):
        acc = None
        for i in range(0, len(test[c]), chunk):
            a = dl.attribute(test[c][i:i + chunk], bg, target=c)
            a = a.detach().squeeze(1).sum(axis=0).sum(axis=0).cpu().numpy()
            acc = a if acc is None else acc + a
        out.append(acc)
        if (c + 1) % 25 == 0:
            log(f"    [B] attributed {c+1}/{n_classes} classes "
                f"({time.time()-t0:.0f}s)")
    return np.array(out)


def effective_ranges(attr_values):
    """[30%, 60%] band of the cumulative attribution curve, as percentages of
    load time. Transcribed from data_augmentation.py."""
    rng = {}
    n = attr_values.shape[1]
    for c in range(attr_values.shape[0]):
        cum = np.cumsum(attr_values[c])
        m = cum.max()
        if m <= 0:                      # degenerate, fall back to the whole trace
            rng[c] = (30, 60)
            continue
        cum = cum / m
        lo = int(np.searchsorted(cum, ATTR_LO, side="right") * 100 // n)
        hi = int(np.searchsorted(cum, ATTR_HI, side="right") * 100 // n)
        if hi <= lo:
            hi = lo + 1
        rng[c] = (max(lo, 1), min(max(hi, 2), 100))
    return rng


# ------------------------------------------------------------------- stage C

def augment(X, T, y, ranges, seed, num_aug=NUM_AUG):
    """Two truncated copies of each trace plus the original.

    The cut point is a random percentage inside that class's effective range,
    applied to the trace's own load time. Truncation keeps the first k packets,
    which is what their `X[index][:valid_length]` does given that timestamps are
    monotonic.
    """
    rs = np.random.RandomState(seed)
    real = X != 0
    lens = real.sum(1)
    n, L = X.shape
    nX = np.zeros(((num_aug + 1) * n, L), dtype=X.dtype)
    nT = np.zeros(((num_aug + 1) * n, L), dtype=T.dtype)
    ny = np.zeros((num_aug + 1) * n, dtype=y.dtype)
    w = 0
    for i in range(n):
        Li = lens[i]
        load = T[i, Li - 1] if Li > 0 else 0.0
        lo, hi = ranges[int(y[i])]
        for _ in range(num_aug):
            p = rs.randint(lo, hi) if hi > lo else lo
            thr = load * p / 100.0
            k = int(np.searchsorted(T[i, :Li], thr, side="right"))
            k = max(k, 1)
            nX[w, :k] = X[i, :k]
            nT[w, :k] = T[i, :k]
            ny[w] = y[i]
            w += 1
        nX[w, :Li] = X[i, :Li]
        nT[w, :Li] = T[i, :Li]
        ny[w] = y[i]
        w += 1
    return nX[:w], nT[:w], ny[:w]


# ------------------------------------------------------------------- stage D

@torch.no_grad()
def embed(net, Xg, batch=256):
    net.eval()
    return torch.cat([net(Xg[i:i + batch]).cpu() for i in range(0, len(Xg), batch)])


@torch.no_grad()
def knn_monitor(net, Xm, ym, Xq, yq, n_classes, k, t):
    """WFlib model_utils.knn_monitor, cosine-similarity weighted kNN vote."""
    net.eval()
    bank = F.normalize(embed(net, Xm).to(DEV), dim=1).t().contiguous()
    labels = torch.as_tensor(np.asarray(ym, dtype=np.int64), device=DEV)
    preds = []
    for i in range(0, len(Xq), 256):
        f = F.normalize(net(Xq[i:i + 256]), dim=1)
        sim = f @ bank
        sw, si = sim.topk(k=min(k, bank.shape[1]), dim=-1)
        sl = labels[si]
        sw = (sw / t).exp()
        one = torch.zeros(f.size(0) * sl.shape[1], n_classes, device=DEV)
        one.scatter_(-1, sl.reshape(-1, 1), 1.0)
        scores = (one.view(f.size(0), -1, n_classes) * sw.unsqueeze(-1)).sum(1)
        preds.append(scores.argmax(1).cpu())
    return torch.cat(preds).numpy()


def train_stage_d(Xf, yf_np, Xv, yv_np, n_classes, seed, log):
    from pytorch_metric_learning import losses
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    net = holmes.HolmesNet().to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=STAGE_D["lr"])
    crit = losses.SupConLoss(temperature=STAGE_D["temperature"])
    yf = torch.from_numpy(yf_np.astype(np.int64)).to(DEV)
    g = torch.Generator(device=DEV); g.manual_seed(seed)
    best_f1, best_state = -1.0, None
    for ep in range(STAGE_D["epochs"]):
        net.train()
        perm = torch.randperm(len(Xf), device=DEV, generator=g)
        tot = 0.0
        for i in range(0, len(Xf), STAGE_D["batch"]):
            idx = perm[i:i + STAGE_D["batch"]]
            if len(idx) < 2:
                continue
            opt.zero_grad(set_to_none=True)
            loss = crit(net(Xf[idx]), yf[idx])
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        pred = knn_monitor(net, Xf, yf_np, Xv, yv_np, n_classes,
                           STAGE_D["knn_k"], STAGE_D["knn_t"])
        f1 = f1_score(yv_np, pred, average="macro")
        if f1 > best_f1:
            best_f1, best_state = f1, {k: v.detach().clone()
                                       for k, v in net.state_dict().items()}
        if (ep + 1) % 5 == 0 or ep == 0:
            log(f"    [D] epoch {ep+1:2d} supcon {tot/len(Xf):.4f} "
                f"kNN validF1 {f1:.4f} (best {best_f1:.4f})")
    net.load_state_dict(best_state)
    log(f"    [D] best kNN valid macroF1 {best_f1:.4f}")
    return net, best_f1


# ----------------------------------------------------------------- the driver

def taf_gpu(X, T):
    return torch.from_numpy(holmes.taf_input(X, T)).to(DEV)


def run_axis(axis, seeds, cells_filter, log):
    (Xtr, Ttr, ytr), tests, labels = data.axis_split(axis)
    n_classes = len(labels)
    rows = []

    # TAF for the evaluation cells is seed independent, build once
    t0 = time.time()
    test_taf = {k: (taf_gpu(v[0], v[1]), v[2]) for k, v in tests.items()}
    log(f"  test TAF built in {time.time()-t0:.0f}s")

    for seed in seeds:
        t_seed = time.time()
        ia, ih = train_test_split(np.arange(len(ytr)), test_size=HOLDOUT,
                                  stratify=ytr, random_state=seed)
        ifit, ival = train_test_split(ia, test_size=VALID_FRAC,
                                      stratify=ytr[ia], random_state=seed)
        log(f"  seed {seed}: fit {len(ifit)}, valid {len(ival)}, "
            f"holdout {len(ih)}")

        # ---- stage A
        Xa = torch.from_numpy(holmes.temporal_input(Xtr[ifit], Ttr[ifit])).to(DEV)
        Xav = torch.from_numpy(holmes.temporal_input(Xtr[ival], Ttr[ival])).to(DEV)
        ya = torch.from_numpy(ytr[ifit].astype(np.int64)).to(DEV)
        net_a, f1_a = train_stage_a(Xa, ya, Xav, ytr[ival], n_classes, seed, log)

        # ---- stage B
        attr = feature_attr(net_a, Xav, ytr[ival], n_classes, log)
        rngs = effective_ranges(attr)
        spans = [hi - lo for lo, hi in rngs.values()]
        log(f"    [C] effective ranges: median {int(np.median([l for l,_ in rngs.values()]))}"
            f"-{int(np.median([h for _,h in rngs.values()]))}%, "
            f"median span {int(np.median(spans))}%")
        del Xa, Xav, net_a
        torch.cuda.empty_cache()

        # ---- stage C
        aXf, aTf, ayf = augment(Xtr[ifit], Ttr[ifit], ytr[ifit], rngs, seed)
        aXv, aTv, ayv = augment(Xtr[ival], Ttr[ival], ytr[ival], rngs, seed + 1000)

        # ---- stage D
        t0 = time.time()
        Xd = taf_gpu(aXf, aTf)
        Xdv = taf_gpu(aXv, aTv)
        log(f"    [D] train TAF {tuple(Xd.shape)} + valid {tuple(Xdv.shape)} "
            f"in {time.time()-t0:.0f}s, {torch.cuda.memory_allocated()/2**30:.1f} GiB")
        net_d, f1_d = train_stage_d(Xd, ayf, Xdv, ayv, n_classes, seed, log)

        # ---- calibration on the augmented validation set
        ev = embed(net_d, Xdv).numpy()
        centroids, radii = holmes.spatial_distribution(ev, ayv, n_classes)
        del Xd, Xdv
        torch.cuda.empty_cache()

        # ---- evaluate
        hold_taf = taf_gpu(Xtr[ih], Ttr[ih])
        cells = {"in-dist": (hold_taf, ytr[ih])}
        cells.update(test_taf)
        for cell, (Xg, yte) in cells.items():
            if cells_filter and cell not in cells_filter:
                continue
            pred = holmes.predict_from_distribution(embed(net_d, Xg).numpy(),
                                                    centroids, radii)
            rows.append({
                "axis": axis, "cell": cell, "seed": seed,
                "accuracy": float(accuracy_score(yte, pred)),
                "f1_macro": float(f1_score(yte, pred, average="macro")),
                "f1_micro": float(f1_score(yte, pred, average="micro")),
                "n_train": int(len(ifit)), "n_test": int(len(yte)),
                "n_classes": n_classes,
                "stage_a_valid_f1": round(float(f1_a), 4),
                "stage_d_knn_valid_f1": round(float(f1_d), 4),
                "fit_seconds": round(time.time() - t_seed, 1),
            })
            log(f"  seed {seed} {axis}/{cell}: acc={rows[-1]['accuracy']:.4f} "
                f"macroF1={rows[-1]['f1_macro']:.4f}")
        del hold_taf, net_d
        torch.cuda.empty_cache()
    del test_taf
    torch.cuda.empty_cache()
    return rows


def write(out, rows):
    """Checkpoint results after each axis. A crash in a later axis then costs
    only that axis, not the hours already spent on the earlier one."""
    json.dump({"classifier": "Holmes", "world": "closed",
               "pipeline": "4-stage, WFlib scripts/Holmes.sh",
               "hyperparameters": {"stage_a": STAGE_A, "stage_d": STAGE_D,
                                   "num_aug": NUM_AUG, "valid_frac": VALID_FRAC,
                                   "attr_band": [ATTR_LO, ATTR_HI],
                                   "n_bg": N_BG, "n_attr": N_ATTR},
               "device": torch.cuda.get_device_name(0) if DEV == "cuda" else "cpu",
               "torch": torch.__version__, "rows": rows},
              open(out, "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--axes", nargs="+", default=["cross-network", "drift"])
    ap.add_argument("--cells", nargs="+", default=None)
    ap.add_argument("--tag", default="holmes")
    a = ap.parse_args()
    if DEV != "cuda":
        print("REFUSING: no CUDA device.")
        return 1
    print(f"device {torch.cuda.get_device_name(0)}  torch {torch.__version__}")
    torch.backends.cudnn.benchmark = True

    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, f"{a.tag}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    rows = []
    for axis in a.axes:
        print(f"== Holmes / {axis} ==")
        rows += run_axis(axis, list(range(a.seeds)), a.cells, print)
        write(out, rows)                 # checkpoint after each axis
        print(f"  checkpointed {len(rows)} rows to {out}")

    json.dump({"classifier": "Holmes", "world": "closed",
               "pipeline": "4-stage, WFlib scripts/Holmes.sh",
               "hyperparameters": {"stage_a": STAGE_A, "stage_d": STAGE_D,
                                   "num_aug": NUM_AUG, "valid_frac": VALID_FRAC,
                                   "attr_band": [ATTR_LO, ATTR_HI]},
               "device": torch.cuda.get_device_name(0),
               "torch": torch.__version__, "rows": rows},
              open(out, "w"), indent=1)
    print(f"\nwrote {out}")
    print("\nsummary (mean +/- sd over seeds)")
    for axis in sorted({r["axis"] for r in rows}):
        for cell in sorted({r["cell"] for r in rows if r["axis"] == axis}):
            v = [r["f1_macro"] for r in rows if r["axis"] == axis and r["cell"] == cell]
            print(f"  {axis:14s} {cell:8s} macroF1 {np.mean(v):.4f} +/- {np.std(v):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
