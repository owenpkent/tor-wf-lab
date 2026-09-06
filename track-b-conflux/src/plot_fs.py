#!/usr/bin/env python3
"""Figure for the Track B kill test: results/fs-rate.png

Two stacked panels sharing the latency-advantage axis. Separate panels rather
than a second y-axis, because a rate and a cell count are different scales.
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
S1, S2 = "#2a78d6", "#eb6834"          # validated categorical slots 1 and 2
GRID = "#e2e1dc"

d = json.load(open(os.path.join(ROOT, "results", "fs-sweep.json")))
rows = sorted(d["sweep"], key=lambda r: r["advantage_ms"])
x = [r["advantage_ms"] for r in rows]
fs = [r["fs_rate"] for r in rows]
c_fs = [r["median_cells_fs"] for r in rows]
c_non = [r["median_cells_nonfs"] for r in rows]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=True,
                               gridspec_kw={"height_ratios": [1, 1], "hspace": 0.18})
fig.patch.set_facecolor(SURFACE)

for ax in (ax1, ax2):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9, length=0)

# Panel 1: one series, so no legend. The title names it.
ax1.plot(x, fs, color=S1, linewidth=2, marker="o", markersize=8,
         markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
ax1.set_ylim(0, 1.05)
ax1.set_ylabel("first-segment rate", color=INK2, fontsize=10)
ax1.set_title("A guard's latency advantage buys the start of the page load",
              color=INK, fontsize=12, loc="left", pad=12)
for xi, yi in ((0, fs[0]), (128, fs[3]), (512, fs[5])):
    ax1.annotate(f"{yi:.2f}", (xi, yi), textcoords="offset points",
                 xytext=(0, 12), ha="center", color=INK, fontsize=9)

# Panel 2: two series, so legend plus direct labels.
ax2.plot(x, c_fs, color=S1, linewidth=2, marker="o", markersize=8,
         markeredgecolor=SURFACE, markeredgewidth=2, label="first-segment legs", zorder=3)
ax2.plot(x, c_non, color=S2, linewidth=2, marker="s", markersize=8,
         markeredgecolor=SURFACE, markeredgewidth=2, label="other legs", zorder=3)
ax2.annotate("first-segment legs", (x[-1], c_fs[-1]), textcoords="offset points",
             xytext=(-6, 10), ha="right", color=INK, fontsize=9)
ax2.annotate("other legs", (x[-1], c_non[-1]), textcoords="offset points",
             xytext=(-6, -18), ha="right", color=INK, fontsize=9)
ax2.set_ylabel("median cells seen by the guard", color=INK2, fontsize=10)
ax2.set_xlabel("guard latency advantage (ms)", color=INK2, fontsize=10)
leg = ax2.legend(frameon=False, fontsize=9, loc="upper left")
for t in leg.get_texts():
    t.set_color(INK2)

fig.text(0.5, 0.015,
         "Conflux traces, CA client, month 2, osf.io/9m8ea. Detector from thesis 4.3.2. "
         "n = 18k-35k per point.",
         ha="center", color=INK2, fontsize=8)
out = os.path.join(ROOT, "results", "fs-rate.png")
fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=SURFACE)
print("wrote", out)
