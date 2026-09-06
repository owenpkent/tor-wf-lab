# Track A on the 5090 machine

Everything CPU-shaped is done: data staged and verified, paper numbers checked,
k-FP run on both axes. What is left is the four CNNs, and they are the whole
reason the brief asked for a GPU. Work top to bottom, and stop at a failed gate
rather than continuing.

## 0. Setup, about 20 minutes

```bash
git clone https://github.com/owenpkent/tor-wf-lab && cd tor-wf-lab
python3 -m venv .venv && .venv/bin/pip install numpy scipy scikit-learn matplotlib joblib
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu128
```

Blackwell is sm_120, so cu128 or newer. Confirm before anything else:

```bash
.venv/bin/python -c "import torch; print(torch.__version__, torch.cuda.get_device_capability())"
```

Expect `(12, 0)`. If it prints `sm_120 is not compatible`, the wheel is too old
and every run below is worthless.

Data, five files and about 1.9 GB, is all the two axes need:

```bash
.venv/bin/python track-a-robustness/src/fetch_osf.py \
  pre-month0-cfx0-au.npz pre-month0-cfx0-ca.npz \
  post-month0-cfx0-uk.npz post-month2-cfx0-uk.npz post-month6-cfx0-uk.npz
.venv/bin/python track-a-robustness/src/verify_osf.py
```

The patterns end in `.npz` deliberately, which excludes the `-nga` variants.
`verify_osf.py` will report the other 24 as missing; only the five matter.

Write the GPU, driver, CUDA and torch versions into `logs/deltas.md` before
running anything.

## 1. What already exists

All of it is written and smoke-tested on CPU. The GPU machine should not need to
write code, only to run it.

| File | What it does |
|---|---|
| `src/data.py` | `axis_split("cross-network" \| "drift")` returns train, test cells and the label intersection |
| `src/models.py` | DF, Tik-Tok and RF architectures, input transforms, TAM builder, and `SPECS` holding Table C.1 verbatim |
| `src/cache_tam.py` | Precomputes the RF TAM cache into `data/cache/`, 763 MB over five files. `data/` is gitignored, so **run this once on the GPU box**: it takes about 10 seconds total and `run_torch.py rf` calls it automatically if the cache is absent |
| `src/run_torch.py` | The runner. Same 20% holdout protocol and JSON row schema as `run_kfp.py` |
| `src/plot_axes.py` | The deliverable scatter. Reads every `results/*.json` and names any classifier that has not run |
| `results/kfp.json` | k-FP already finished, both axes, 3 seeds |

Commands:

```bash
.venv/bin/python track-a-robustness/src/run_torch.py df
.venv/bin/python track-a-robustness/src/run_torch.py tiktok
.venv/bin/python track-a-robustness/src/run_torch.py rf
.venv/bin/python track-a-robustness/src/run_torch.py rf --tam-slots 300 --tag=-tam300
.venv/bin/python track-a-robustness/src/run_torch.py rf --tam-slots 150 --tag=-tam150
.venv/bin/python track-a-robustness/src/plot_axes.py
```

`--epochs` and `--limit` exist for smoke tests only; never use them for a
reported number. The TAM cache is stored at the published 1800 slots and
downsampled exactly for the 300 and 150 slot runs, so the sweep needs no rebuild.

### What the smoke tests established

On CPU, with a subsample and 3 epochs, all three models train, evaluate and
write results. DF reached 0.417 in-distribution accuracy against 0.0097 chance
after 3 epochs on 2,400 traces, which is the pipeline working end to end rather
than a result. One real bug was caught and fixed this way: `RFNet` sized its
classifier from the default 1800 slots rather than from the input, so the
slot-size sweep crashed.

Timing on this laptop's CPU, for calibration only: DF is about 21 s per epoch
per 2,400 traces, so roughly 70 minutes for one full 30-epoch run. If the 5090
is not at least twenty times faster than that, something is wrong.

### Holmes

Not implemented, on purpose, and `plot_axes.py` will print it under "not run".
Table C.1 gives it two branches, two optimizers, two batch sizes and an
unweighted CrossEntropy plus SupConLoss mix. See `logs/deltas.md`.

## 2. Hyperparameters, thesis Table C.1, do not retune

Full table in `logs/paper-numbers.md`. Architectures come from the original
papers, since the authors released none.

| | DF | Tik-Tok | RF | Holmes |
|---|---|---|---|---|
| Type | 1D CNN | 1D CNN | 2D CNN | dual-branch CNN |
| Input | direction, len 5000 | direction x timestamp, len 5000 | TAM, len 1800 | temporal 1000 / TAF 2000 |
| Batch | 128 | 32 | 200 | 200 / 256 |
| Epochs | 30 | 30 max | 30 | 30 |
| Optimizer | Adamax | Adamax | Adam | Adam / AdamW |
| LR | 0.002 | 0.002 | 5e-4 x 0.2^(epoch/30) | 0.0005 |
| Loss | CrossEntropy | CrossEntropy | CrossEntropy | CrossEntropy / SupConLoss |
| Other | b1 .9 b2 .999 eps 1e-8 | same, early stop val_loss patience 6 | Tmax per experiment | best-F1 epoch selection |

Two things the table leaves to you, so both go in `deltas.md`:

- Tik-Tok's early stopping needs a validation split the paper never sizes. Take
  it out of the 80% training portion, not the in-distribution holdout, or the
  anchor stops being held out.
- The TAM `Tmax`. Measured on the actual files: **every collection caps at
  exactly 45.00 s**, median load 9 to 15 s. So the per-experiment setting the
  thesis describes gives Tmax = 45, and with N = 1800 that is a **25 ms slot**,
  finer than the 44 ms default. Appendix C.1 says fine slots are what destroy RF
  across networks, so record the exact Tmax you used next to every RF number.

## 3. Order of work, with gates

**Gate 1, DF in-distribution.** DF on the cross-network axis, seed 0, evaluate
the held-out AU cell only. Closed-world macro F1 should be at least about 0.95,
since k-FP already gets 0.958 there and DF beats k-FP everywhere in the paper.
Below roughly 0.90 means the harness is wrong, not the model. Stop and debug.

**Gate 2, DF cross-network.** Same model, CA cell. The paper's claim is that DF
survives network mismatch, so expect a modest drop, not a collapse. A collapse
here means the two-axis picture cannot be built from this data and is worth
reporting on its own.

**Then the rest**, 3 seeds, both axes, all cells: DF, Tik-Tok, RF.

**RF deserves a second run.** Its whole story is Appendix C.1: slot size versus
the roughly 150 ms AU-CA latency delta. Run it at the per-experiment Tmax (45 s,
N = 1800, 25 ms slots) for the main table, then repeat the cross-network cell at
N = 300 and N = 150, which give 150 ms and 300 ms slots. That is reproducing the
authors' own documented sweep, not retuning, but report it as a separate
sensitivity line and never fold it into the main table. If RF recovers there,
the "distinct axes" claim is really a statement about one preprocessing constant.

**Holmes is already decided: not run.** Table C.1 gives it two branches, two
optimizers and a SupConLoss with no weighting, which is not enough to
reimplement faithfully, so it is deliberately absent from `models.py` and
`plot_axes.py` prints it under "not run". A missing point on the scatter is
honest; an approximated Holmes is a number that looks like a measurement and is
not one. Revisit only if the authors send code.

## 4. Runtime

The whole grid is small by GPU standards: about 17k training traces of 5000
cells, 103 to 106 classes, 30 epochs. On a 5090 expect single-digit minutes per
training run, so 4 models x 3 seeds x 2 axes lands in roughly one to two hours
including data loading. If a single run is taking an hour, something is on the
CPU that should not be, most likely the TAM or TAF construction. Precompute
those once per collection and cache them.

## 5. Deliverable

`src/plot_axes.py` is written and runs today against `results/kfp.json` alone,
printing "not run: DF, Tik-Tok, RF, Holmes" and drawing the one point it has. As
each model finishes, rerun it and the point appears. x is cross-network CA macro
F1, y is drift month-6 macro F1, error bars are the seed spread, and both axes
are labelled closed-world in the figure itself, because the plot will outlive the
caption explaining that it is not the paper's open-world measurement.

k-FP's point is already known: **(0.797, 0.487)**.

Then the verdict paragraph, which has to answer three things:

1. Do classifiers actually trade places across the two axes, or do they simply
   rank the same on both?
2. Does the RF slot-size sweep explain its cross-network position away?
3. What does closed-world scoring cost the comparison? k-FP's cross-network cell
   moved 0.430 -> 0.797 when the background set disappeared, so the gap between
   the two worlds is larger than most of the gaps being compared.
