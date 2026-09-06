#!/usr/bin/env python3
"""results/fs-kfp.png: what first-segment ownership is worth, measured."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e2e1dc"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # validated; all three direct-labelled,
                                               # which covers the aqua contrast WARN

rows = json.load(open(os.path.join(ROOT, "results", "fs-kfp.json")))["rows"]
adv = sorted({r["advantage_ms"] for r in rows})


def series(key):
    m = [np.mean([r[key] for r in rows if r["advantage_ms"] == a]) for a in adv]
    s = [np.std([r[key] for r in rows if r["advantage_ms"] == a]) for a in adv]
    return np.array(m), np.array(s)

fs_m, fs_s = series("acc_fs")
non_m, non_s = series("acc_nonfs")
all_m, all_s = series("acc_all")

fig, ax = plt.subplots(figsize=(7.2, 4.8))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
ax.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color(GRID)
ax.tick_params(colors=INK2, labelsize=9, length=0)

for m, sd, c, lab, mk in ((fs_m, fs_s, S1, "traces where the guard owns the first segment", "o"),
                          (all_m, all_s, S3, "all traces", "^"),
                          (non_m, non_s, S2, "traces where it does not", "s")):
    ax.plot(adv, m, color=c, linewidth=2, marker=mk, markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2, label=lab, zorder=3)
    ax.fill_between(adv, m - sd, m + sd, color=c, alpha=0.15, linewidth=0)

ax.annotate("owns the first segment", (adv[-1], fs_m[-1]), textcoords="offset points",
            xytext=(-8, 10), ha="right", color=INK, fontsize=9)
ax.annotate("all traces", (adv[-1], all_m[-1]), textcoords="offset points",
            xytext=(-8, -20), ha="right", color=INK, fontsize=9)
ax.annotate("does not", (adv[-1], non_m[-1]), textcoords="offset points",
            xytext=(-8, 10), ha="right", color=INK, fontsize=9)

ax.set_ylim(0, 1)
ax.set_xlabel("guard latency advantage (ms)", color=INK2, fontsize=10)
ax.set_ylabel("k-FP closed-world accuracy", color=INK2, fontsize=10)
ax.set_title("Owning the first segment matters far more than owning more of it",
             color=INK, fontsize=12, loc="left", pad=12)
leg = ax.legend(frameon=False, fontsize=9, loc="lower left")
for t in leg.get_texts():
    t.set_color(INK2)
fig.text(0.5, -0.02,
         "107 classes, 3 seeds, chance 0.009. Bands are the seed spread. At 512 ms only 87 test traces "
         "are non-first-segment.",
         ha="center", color=INK2, fontsize=8)

dest = os.path.join(ROOT, "results", "fs-kfp.png")
fig.savefig(dest, dpi=160, bbox_inches="tight", facecolor=SURFACE)
print("wrote", dest)
