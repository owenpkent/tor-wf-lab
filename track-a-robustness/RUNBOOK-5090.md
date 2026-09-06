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

## 1. What already exists, reuse it

- `src/data.py` -> `axis_split("cross-network" | "drift")` returns
  `(Xtr, Ttr, ytr), {cell: (X, T, y)}, labels`, already restricted to the label
  intersection for that axis. `X` is int8 direction, `T` float32 seconds, both
  (n, 5000) zero-padded.
- `src/run_kfp.py` is the protocol to copy: 20% stratified holdout per seed as
  the in-distribution anchor, seeds 0/1/2, one JSON row per (axis, cell, seed)
  with `accuracy`, `f1_macro`, `f1_micro`, `n_train`, `n_test`, `n_classes`.
  Keep that row schema so the plot script can eat all five classifiers.
- `results/kfp.json`, `results/kfp-summary.md` are k-FP's finished cells.

Write `src/models.py` (architectures + input transforms) and `src/run_torch.py`
(mirror of `run_kfp.py`, takes a model name), emitting `results/<model>.json`.

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

**Then the rest**, 3 seeds, both axes, all cells: DF, Tik-Tok, RF, Holmes.

**RF deserves a second run.** Its whole story is Appendix C.1: slot size versus
the roughly 150 ms AU-CA latency delta. Run it at the per-experiment Tmax (45 s,
N = 1800, 25 ms slots) for the main table, then repeat the cross-network cell at
N = 300 and N = 150, which give 150 ms and 300 ms slots. That is reproducing the
authors' own documented sweep, not retuning, but report it as a separate
sensitivity line and never fold it into the main table. If RF recovers there,
the "distinct axes" claim is really a statement about one preprocessing constant.

**Holmes last, and it is allowed to fail.** Table C.1 gives it two branches, two
optimizers and a SupConLoss with no weighting, which is not enough to reimplement
faithfully. If it cannot be built with confidence, report Holmes as not run. A
missing point on the scatter plot is honest; an approximated Holmes is a number
that looks like a measurement and is not one.

## 4. Runtime

The whole grid is small by GPU standards: about 17k training traces of 5000
cells, 103 to 106 classes, 30 epochs. On a 5090 expect single-digit minutes per
training run, so 4 models x 3 seeds x 2 axes lands in roughly one to two hours
including data loading. If a single run is taking an hour, something is on the
CPU that should not be, most likely the TAM or TAF construction. Precompute
those once per collection and cache them.

## 5. Deliverable

`src/plot_axes.py`: read every `results/*.json`, one point per classifier,
x = cross-network CA macro F1, y = drift month-6 macro F1, error bars from the
3 seeds. k-FP's point is already known: **(0.797, 0.487)**.

Label both axes closed-world macro F1 in the figure itself. These are not the
paper's open-world numbers and the plot will outlive the caption explaining that.

Then the verdict paragraph, which has to answer three things:

1. Do classifiers actually trade places across the two axes, or do they simply
   rank the same on both?
2. Does the RF slot-size sweep explain its cross-network position away?
3. What does closed-world scoring cost the comparison? k-FP's cross-network cell
   moved 0.430 -> 0.797 when the background set disappeared, so the gap between
   the two worlds is larger than most of the gaps being compared.
