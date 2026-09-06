#!/usr/bin/env python3
"""Train one CNN classifier closed-world on both axes, 3+ seeds.

Mirror of run_kfp.py: same 20% stratified in-distribution holdout per seed,
same per-(axis, cell, seed) row schema, so results/*.json from every classifier
can be read by one plot script.

Usage:
  python run_torch.py df
  python run_torch.py tiktok --seeds 3
  python run_torch.py rf --slots 300 --tag rf-n300
  python run_torch.py df --axes cross-network --seeds 1 --cells in-dist   # gate

Hyperparameters are thesis Table C.1 and are not retuned. Architectures come
from each classifier's own paper / released code, see models.py.
"""
import argparse, json, os, sys, time
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data, models

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
HOLDOUT = 0.2            # in-distribution anchor, matches run_kfp.py
DEV = "cuda" if torch.cuda.is_available() else "cpu"

# Thesis Table C.1. Do not retune; record any deviation in logs/deltas.md.
CONFIG = {
    "df":     dict(name="DF",      net="DFNet", tf="df",     batch=128,
                   epochs=30, opt="adamax", lr=0.002, sched=None, patience=None),
    "tiktok": dict(name="Tik-Tok", net="DFNet", tf="tiktok", batch=32,
                   epochs=30, opt="adamax", lr=0.002, sched=None, patience=6,
                   val_frac=0.1),
    "rf":     dict(name="RF",      net="RFNet", tf="rf",     batch=200,
                   epochs=30, opt="adam",   lr=5e-4, sched="rf", patience=None),
}


def build_inputs(model, X, T, slots, tmax):
    cfg = CONFIG[model]
    tf = models.TRANSFORMS[cfg["tf"]]
    if cfg["tf"] == "rf":
        a = tf(X, T, n_slots=slots, tmax=tmax)
        a = a[:, None, :, :]              # (n, 1, 2, slots), as in RF/train.py
    else:
        a = tf(X, T)
    return torch.from_numpy(np.ascontiguousarray(a))


def make_net(model, n_classes, in_len):
    if CONFIG[model]["net"] == "DFNet":
        return models.DFNet(n_classes, in_len=in_len)
    return models.RFNet(n_classes)


def make_opt(model, net):
    cfg = CONFIG[model]
    if cfg["opt"] == "adamax":
        # Table C.1: beta1 .9, beta2 .999, eps 1e-8 (torch defaults)
        return torch.optim.Adamax(net.parameters(), lr=cfg["lr"],
                                  betas=(0.9, 0.999), eps=1e-8)
    return torch.optim.Adam(net.parameters(), lr=cfg["lr"])


@torch.no_grad()
def predict(net, Xg, batch=512):
    net.eval()
    out = []
    for i in range(0, len(Xg), batch):
        out.append(net(Xg[i:i + batch]).argmax(1).cpu())
    return torch.cat(out).numpy()


def train_one(model, Xtr, ytr, n_classes, seed, log=print):
    """Train on (Xtr, ytr), already resident on the GPU. Returns (net, info)."""
    cfg = CONFIG[model]
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    net = make_net(model, n_classes, Xtr.shape[-1]).to(DEV)
    opt = make_opt(model, net)
    sched = None
    if cfg["sched"] == "rf":
        # Table C.1: 5e-4 x 0.2^(epoch/30)
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda e: 0.2 ** (e / 30))
    lossf = nn.CrossEntropyLoss()

    # Tik-Tok's early stopping needs a validation split the paper never sizes.
    # It comes out of the training portion, never out of the in-distribution
    # holdout, or the anchor would stop being held out. See logs/deltas.md.
    Xva = yva = None
    if cfg["patience"]:
        ytr_np = ytr.cpu().numpy()
        itr, iva = train_test_split(np.arange(len(ytr_np)), test_size=cfg["val_frac"],
                                    stratify=ytr_np, random_state=seed)
        itr_t = torch.from_numpy(itr).to(DEV)
        iva_t = torch.from_numpy(iva).to(DEV)
        Xva, yva = Xtr[iva_t], ytr[iva_t]
        Xtr, ytr = Xtr[itr_t], ytr[itr_t]

    n = len(Xtr)
    best_val, best_state, best_epoch, bad = float("inf"), None, -1, 0
    g = torch.Generator(device=DEV)
    g.manual_seed(seed)
    t0 = time.time()
    epochs_run = 0
    for ep in range(cfg["epochs"]):
        net.train()
        perm = torch.randperm(n, device=DEV, generator=g)
        tot = 0.0
        for i in range(0, n, cfg["batch"]):
            idx = perm[i:i + cfg["batch"]]
            if len(idx) < 2:
                continue                      # BatchNorm needs >1 sample
            opt.zero_grad(set_to_none=True)
            loss = lossf(net(Xtr[idx]), ytr[idx])
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        if sched:
            sched.step()
        epochs_run = ep + 1

        if Xva is not None:
            net.eval()
            with torch.no_grad():
                vl = sum(lossf(net(Xva[i:i + 512]), yva[i:i + 512]).item()
                         * len(yva[i:i + 512])
                         for i in range(0, len(Xva), 512)) / len(Xva)
            log(f"    epoch {ep+1:2d} train_loss {tot/n:.4f} val_loss {vl:.4f}")
            if vl < best_val - 1e-6:
                best_val, best_epoch, bad = vl, ep + 1, 0
                best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= cfg["patience"]:
                    log(f"    early stop at epoch {ep+1}, best {best_epoch} "
                        f"(val_loss {best_val:.4f})")
                    break
        elif (ep + 1) % 10 == 0 or ep == 0:
            log(f"    epoch {ep+1:2d} train_loss {tot/n:.4f}")

    if best_state is not None:
        net.load_state_dict(best_state)
    return net, {"fit_seconds": round(time.time() - t0, 1),
                 "epochs_run": epochs_run, "best_epoch": best_epoch}


def evaluate(model, axis, seeds, slots, tmax, cells_filter=None, log=print):
    (Xtr_r, Ttr, ytr), tests, labels = data.axis_split(axis)
    n_classes = len(labels)

    t0 = time.time()
    Xtr_t = build_inputs(model, Xtr_r, Ttr, slots, tmax).to(DEV)
    ytr_t = torch.from_numpy(ytr.astype(np.int64)).to(DEV)
    test_t = {k: (build_inputs(model, v[0], v[1], slots, tmax).to(DEV), v[2])
              for k, v in tests.items()}
    log(f"  inputs built in {time.time()-t0:.0f}s, train {tuple(Xtr_t.shape)}, "
        f"{torch.cuda.memory_allocated()/2**30:.1f} GiB on device")

    rows = []
    for seed in seeds:
        ia, ih = train_test_split(np.arange(len(ytr)), test_size=HOLDOUT,
                                  stratify=ytr, random_state=seed)
        ia_t, ih_t = torch.from_numpy(ia).to(DEV), torch.from_numpy(ih).to(DEV)
        net, info = train_one(model, Xtr_t[ia_t], ytr_t[ia_t], n_classes, seed, log=log)

        cells = {"in-dist": (Xtr_t[ih_t], ytr[ih])}
        cells.update({k: (Xg, yte) for k, (Xg, yte) in test_t.items()})
        for cell, (Xg, yte) in cells.items():
            if cells_filter and cell not in cells_filter:
                continue
            pred = predict(net, Xg)
            row = {"axis": axis, "cell": cell, "seed": seed,
                   "accuracy": float(accuracy_score(yte, pred)),
                   "f1_macro": float(f1_score(yte, pred, average="macro")),
                   "f1_micro": float(f1_score(yte, pred, average="micro")),
                   "n_train": int(len(ia)), "n_test": int(len(yte)),
                   "n_classes": n_classes, **info}
            if CONFIG[model]["tf"] == "rf":
                row.update({"tam_slots": slots, "tam_tmax": tmax,
                            "slot_ms": round(1000 * tmax / (slots - 1), 2)})
            rows.append(row)
            log(f"  seed {seed} {axis}/{cell}: acc={row['accuracy']:.4f} "
                f"macroF1={row['f1_macro']:.4f} (fit {info['fit_seconds']:.0f}s, "
                f"{info['epochs_run']} epochs)")
        del net
        torch.cuda.empty_cache()
    del Xtr_t, ytr_t, test_t
    torch.cuda.empty_cache()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", choices=sorted(CONFIG))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--axes", nargs="+", default=["cross-network", "drift"])
    ap.add_argument("--cells", nargs="+", default=None,
                    help="restrict evaluation cells, e.g. in-dist (for gates)")
    ap.add_argument("--slots", type=int, default=models.TAM_N, help="RF: TAM N")
    ap.add_argument("--tmax", type=float, default=models.TMAX, help="RF: Tmax seconds")
    ap.add_argument("--tag", default=None, help="output basename, default = model")
    a = ap.parse_args()

    if DEV != "cuda":
        print("REFUSING: no CUDA device. These are the GPU classifiers.")
        return 1
    print(f"device {torch.cuda.get_device_name(0)}  torch {torch.__version__}  "
          f"cuda {torch.version.cuda}  cc {torch.cuda.get_device_capability()}")
    torch.backends.cudnn.benchmark = True

    seeds = list(range(a.seeds))
    rows = []
    for axis in a.axes:
        print(f"== {CONFIG[a.model]['name']} / {axis} ==")
        rows += evaluate(a.model, axis, seeds, a.slots, a.tmax, a.cells)

    os.makedirs(RESULTS, exist_ok=True)
    tag = a.tag or a.model
    out = os.path.join(RESULTS, f"{tag}.json")
    payload = {"classifier": CONFIG[a.model]["name"], "world": "closed",
               "hyperparameters": {k: v for k, v in CONFIG[a.model].items()
                                   if k not in ("net", "tf")},
               "device": torch.cuda.get_device_name(0),
               "torch": torch.__version__, "cuda": torch.version.cuda,
               "rows": rows}
    if CONFIG[a.model]["tf"] == "rf":
        payload["tam"] = {"n_slots": a.slots, "tmax": a.tmax,
                          "slot_ms": round(1000 * a.tmax / (a.slots - 1), 2)}
    json.dump(payload, open(out, "w"), indent=1)
    print(f"\nwrote {out}")

    print("\nsummary (mean +/- sd over seeds)")
    for axis in sorted({r["axis"] for r in rows}):
        for cell in sorted({r["cell"] for r in rows if r["axis"] == axis}):
            v = [r["f1_macro"] for r in rows if r["axis"] == axis and r["cell"] == cell]
            print(f"  {axis:14s} {cell:8s} macroF1 {np.mean(v):.4f} +/- {np.std(v):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
