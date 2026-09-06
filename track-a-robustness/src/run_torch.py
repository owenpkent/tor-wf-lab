#!/usr/bin/env python3
"""Run DF / Tik-Tok / RF closed-world on both axes, 3+ seeds.

Mirror of run_kfp.py: same 20% stratified in-distribution holdout per seed, same
JSON row schema, so results/*.json from either script feed the same plot.

  python run_torch.py df
  python run_torch.py rf --tam-slots 300      # Appendix C.1 slot-size sweep
  python run_torch.py tiktok --seeds 3

Closed world only. Nothing produced here is comparable to the paper's
open-world tables; see logs/deltas.md.
"""
import argparse, json, os, sys, time
import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, models
from cache_tam import load_or_build

RESULTS = os.path.join(data.ROOT, "results")
HOLDOUT = 0.2       # in-distribution anchor, as in run_kfp.py
VAL_FRAC = 0.1      # of the training portion, only for Tik-Tok's early stopping


def device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def build_inputs(axis, model, tam_slots):
    """Return (train_tensor, ytr), {cell: (tensor, y)}, n_classes."""
    spec = data.CROSS_NETWORK if axis == "cross-network" else data.DRIFT
    (Xtr, Ttr, ytr), tests, labels = data.axis_split(axis)

    if model == "rf":
        tr = models.tam_input(models.tam_downsample(load_or_build(spec["train"]), tam_slots))
        # The TAM cache is per file, so re-derive the same label restriction.
        _, _, ytr_full = data.load(spec["train"])
        keep = np.isin(ytr_full, labels)
        tr = tr[torch.from_numpy(keep)]
        te = {}
        for cell, relpath in spec["test"].items():
            arr = models.tam_input(models.tam_downsample(load_or_build(relpath), tam_slots))
            _, _, y_full = data.load(relpath)
            k = np.isin(y_full, labels)
            te[cell] = (arr[torch.from_numpy(k)], tests[cell][2])
    else:
        fn = models.SPECS[model]["transform"]
        tr = fn(Xtr, Ttr)
        te = {c: (fn(v[0], v[1]), v[2]) for c, v in tests.items()}
    return (tr, ytr), te, len(labels)


def train_one(spec, Xtr, ytr, n_classes, seed, dev, epochs=None, verbose=True):
    torch.manual_seed(seed)
    net = spec["net"](n_classes, Xtr.shape[-1]).to(dev)
    opt = models.build_optimizer(net, spec)
    sched = (torch.optim.lr_scheduler.LambdaLR(opt, spec["lr_decay"])
             if spec["lr_decay"] else None)
    lossf = torch.nn.CrossEntropyLoss()
    n_epochs = epochs or spec["epochs"]

    idx_tr, idx_val = None, None
    if spec["early_stop"]:
        idx_tr, idx_val = train_test_split(
            np.arange(len(ytr)), test_size=VAL_FRAC, stratify=ytr, random_state=seed)

    y_t = torch.from_numpy(ytr.astype(np.int64))
    order_pool = idx_tr if idx_tr is not None else np.arange(len(ytr))
    best, patience = np.inf, 0

    for epoch in range(n_epochs):
        net.train()
        perm = np.random.default_rng(seed * 1000 + epoch).permutation(order_pool)
        tot = 0.0
        for lo in range(0, len(perm), spec["batch"]):
            b = perm[lo:lo + spec["batch"]]
            if len(b) < 2:                     # BatchNorm needs >1 sample
                continue
            xb = Xtr[b].to(dev, non_blocking=True)
            yb = y_t[b].to(dev, non_blocking=True)
            opt.zero_grad()
            l = lossf(net(xb), yb)
            l.backward()
            opt.step()
            tot += l.item() * len(b)
        if sched:
            sched.step()

        if spec["early_stop"]:
            vl = evaluate_loss(net, Xtr, y_t, idx_val, spec["batch"], dev, lossf)
            if verbose:
                print(f"    epoch {epoch + 1}/{n_epochs} train {tot / len(perm):.4f} val {vl:.4f}")
            if vl < best - 1e-4:
                best, patience = vl, 0
            else:
                patience += 1
                if patience >= spec["early_stop"]:
                    if verbose:
                        print(f"    early stop at epoch {epoch + 1}")
                    break
        elif verbose:
            print(f"    epoch {epoch + 1}/{n_epochs} train {tot / len(perm):.4f}")
    return net


@torch.no_grad()
def evaluate_loss(net, X, y_t, idx, batch, dev, lossf):
    net.eval()
    tot = 0.0
    for lo in range(0, len(idx), batch):
        b = idx[lo:lo + batch]
        tot += lossf(net(X[b].to(dev)), y_t[b].to(dev)).item() * len(b)
    return tot / len(idx)


@torch.no_grad()
def predict(net, X, batch, dev):
    net.eval()
    out = []
    for lo in range(0, len(X), batch):
        out.append(net(X[lo:lo + batch].to(dev)).argmax(1).cpu().numpy())
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=["df", "tiktok", "rf"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--tam-slots", type=int, default=models.TAM_LEN)
    ap.add_argument("--epochs", type=int, default=None, help="override, smoke tests only")
    ap.add_argument("--limit", type=int, default=None, help="subsample, smoke tests only")
    ap.add_argument("--axes", default="cross-network,drift")
    ap.add_argument("--tag", default=None, help="results filename suffix")
    a = ap.parse_args()

    spec = models.SPECS[a.model]
    dev = device()
    print(f"model {a.model}  device {dev}  torch {torch.__version__}"
          + (f"  cuda {torch.version.cuda} sm{torch.cuda.get_device_capability()}"
             if dev.type == "cuda" else "  (CPU: expect this to be slow)"))
    if a.model == "rf":
        print(f"  TAM slots {a.tam_slots}, slot width {models.TAM_TMAX / a.tam_slots * 1000:.1f} ms")

    rows = []
    for axis in a.axes.split(","):
        print(f"== {axis} ==")
        (Xtr, ytr), tests, n_classes = build_inputs(axis, a.model, a.tam_slots)
        if a.limit:
            # random subsample, not a head slice: labels are grouped in the
            # files, so a head slice would cover only a few classes
            def sub(X, y, n):
                i = np.random.default_rng(0).choice(len(y), min(n, len(y)), replace=False)
                return X[i], y[i]
            Xtr, ytr = sub(Xtr, ytr, a.limit)
            tests = {c: sub(v[0], v[1], a.limit) for c, v in tests.items()}
        for seed in range(a.seeds):
            i_fit, i_hold = train_test_split(np.arange(len(ytr)), test_size=HOLDOUT,
                                             stratify=ytr, random_state=seed)
            t0 = time.time()
            net = train_one(spec, Xtr[i_fit], ytr[i_fit], n_classes, seed, dev,
                            epochs=a.epochs)
            fit_s = time.time() - t0
            cells = {"in-dist": (Xtr[i_hold], ytr[i_hold])}
            cells.update(tests)
            for cell, (Xc, yc) in cells.items():
                pred = predict(net, Xc, spec["batch"], dev)
                rows.append({
                    "axis": axis, "cell": cell, "seed": seed, "model": a.model,
                    "accuracy": float(accuracy_score(yc, pred)),
                    "f1_macro": float(f1_score(yc, pred, average="macro")),
                    "f1_micro": float(f1_score(yc, pred, average="micro")),
                    "n_train": int(len(i_fit)), "n_test": int(len(yc)),
                    "n_classes": int(n_classes), "fit_seconds": round(fit_s, 1),
                    "tam_slots": a.tam_slots if a.model == "rf" else None,
                })
                print(f"  seed {seed} {axis}/{cell}: acc={rows[-1]['accuracy']:.4f} "
                      f"macroF1={rows[-1]['f1_macro']:.4f} (fit {fit_s:.0f}s)")

    os.makedirs(RESULTS, exist_ok=True)
    tag = a.tag or (f"-tam{a.tam_slots}" if a.model == "rf" and a.tam_slots != models.TAM_LEN else "")
    dest = os.path.join(RESULTS, f"{a.model}{tag}.json")
    json.dump({"classifier": a.model, "world": "closed", "device": str(dev),
               "torch": torch.__version__, "rows": rows}, open(dest, "w"), indent=1)
    print(f"\nwrote {dest}")

    print("\nsummary (mean +/- sd over seeds)")
    for axis in sorted({r["axis"] for r in rows}):
        for cell in sorted({r["cell"] for r in rows if r["axis"] == axis}):
            v = [r["f1_macro"] for r in rows if r["axis"] == axis and r["cell"] == cell]
            print(f"  {axis:14s} {cell:8s} macroF1 {np.mean(v):.4f} +/- {np.std(v):.4f}")


if __name__ == "__main__":
    main()
