#!/usr/bin/env python3
"""The Track A deliverable: cross-network F1 against six-month F1.

Reads every results/<model>.json written by run_kfp.py or run_torch.py, plots
one point per classifier with error bars over seeds, and prints the underlying
table. Missing classifiers are reported as missing rather than omitted quietly.

  python plot_axes.py                    -> results/axes.png
"""
import glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")

EXPECTED = ["k-FP", "df", "tiktok", "rf", "holmes"]
PRETTY = {"k-FP": "k-FP", "df": "DF", "tiktok": "Tik-Tok", "rf": "RF", "holmes": "Holmes"}
X_CELL = ("cross-network", "ca")        # network mismatch
Y_CELL = ("drift", "month6")            # longest available gap

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e2e1dc"
MARK = "#2a78d6"


def load_all():
    out = {}
    for path in sorted(glob.glob(os.path.join(RESULTS, "*.json"))):
        if "smoke" in os.path.basename(path) or "fs-sweep" in path:
            continue
        d = json.load(open(path))
        rows = d.get("rows", [])
        if not rows:
            continue
        out[d.get("classifier", os.path.basename(path))] = rows
    return out


def cell_stats(rows, axis, cell):
    v = [r["f1_macro"] for r in rows if r["axis"] == axis and r["cell"] == cell]
    return (np.mean(v), np.std(v), len(v)) if v else (None, None, 0)


def main():
    data = load_all()
    pts = []
    print(f"{'classifier':10s} {'cross-network CA':>22s} {'drift month6':>20s}  seeds")
    for key, rows in data.items():
        xm, xs, nx = cell_stats(rows, *X_CELL)
        ym, ys, ny = cell_stats(rows, *Y_CELL)
        if xm is None or ym is None:
            print(f"{PRETTY.get(key, key):10s} incomplete: "
                  f"cross-network={'yes' if xm else 'no'} drift={'yes' if ym else 'no'}")
            continue
        pts.append((PRETTY.get(key, key), xm, xs, ym, ys))
        print(f"{PRETTY.get(key, key):10s} {xm:>13.4f} +/- {xs:.4f} {ym:>11.4f} +/- {ys:.4f}  {min(nx, ny)}")

    missing = [PRETTY[m] for m in EXPECTED if m not in data]
    if missing:
        print(f"\nnot run: {', '.join(missing)}")

    if not pts:
        print("nothing to plot yet")
        return

    fig, ax = plt.subplots(figsize=(6.8, 6.2))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.plot([0, 1], [0, 1], color=GRID, linewidth=1.5, zorder=1)
    ax.text(0.97, 0.99, "equally robust on both axes", color=INK2, fontsize=8,
            rotation=45, ha="right", va="top", rotation_mode="anchor")

    # One hue for every point: identity is carried by the direct label beside
    # each marker, so colour is not doing categorical work here.
    for name, xm, xs, ym, ys in pts:
        ax.errorbar(xm, ym, xerr=xs, yerr=ys, fmt="o", markersize=9,
                    color=MARK, ecolor=MARK, elinewidth=2, capsize=4,
                    markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
        ax.annotate(name, (xm, ym), textcoords="offset points", xytext=(11, 4),
                    color=INK, fontsize=10)

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("cross-network macro F1 (train AU, test CA)", color=INK2, fontsize=10)
    ax.set_ylabel("six-month drift macro F1 (UK month 0 -> month 6)", color=INK2, fontsize=10)
    ax.set_title("Are the two robustness axes distinct?", color=INK, fontsize=13,
                 loc="left", pad=12)
    note = "Closed world, macro F1 over monitored classes. NOT comparable to the paper's open-world tables."
    if missing:
        note += f"  Not run: {', '.join(missing)}."
    fig.text(0.5, 0.005, note, ha="center", color=INK2, fontsize=8, wrap=True)

    dest = os.path.join(RESULTS, "axes.png")
    fig.savefig(dest, dpi=160, bbox_inches="tight", facecolor=SURFACE)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
