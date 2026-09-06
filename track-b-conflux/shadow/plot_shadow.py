#!/usr/bin/env python3
"""results/shadow-sweep.png: does stock tor in Shadow show the latency bias?"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e2e1dc"
S1 = "#2a78d6"

d = json.load(open(os.path.join(ROOT, "results", "shadow-sweep.json")))["points"]
x = [p["advantage_ms"] for p in d]
m = np.array([p["mean"] for p in d])
s = np.array([p["sd"] for p in d])

fig, ax = plt.subplots(figsize=(7.2, 4.6))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
ax.grid(True, color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
for sp in ("left", "bottom"):
    ax.spines[sp].set_color(GRID)
ax.tick_params(colors=INK2, labelsize=9, length=0)

ax.axhline(0.5, color=GRID, linewidth=1.5)
ax.text(500, 0.515, "no bias", color=INK2, fontsize=8, ha="right")
ax.plot(x, m, color=S1, linewidth=2, marker="o", markersize=8,
        markeredgecolor=SURFACE, markeredgewidth=2, zorder=3)
ax.fill_between(x, m - s, m + s, color=S1, alpha=0.15, linewidth=0)

ax.set_ylim(0, 1)
ax.set_xlabel("guard latency advantage (ms RTT)", color=INK2, fontsize=10)
ax.set_ylabel("share of client downstream bytes", color=INK2, fontsize=10)
ax.set_title("Stock tor in Shadow reproduces the latency bias",
             color=INK, fontsize=12, loc="left", pad=12)
fig.text(0.5, -0.03,
         "Shadow 3.3.0, tor 0.4.9.11, unpatched. One client, two pinned guards, 10 seeds per point. "
         "Band is the seed spread.",
         ha="center", color=INK2, fontsize=8)
dest = os.path.join(ROOT, "results", "shadow-sweep.png")
fig.savefig(dest, dpi=160, bbox_inches="tight", facecolor=SURFACE)
print("wrote", dest)
