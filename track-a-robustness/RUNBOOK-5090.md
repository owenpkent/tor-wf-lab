# Track A on the 5090 machine

> **Status: this run is complete.** All five classifiers ran on the 5090 on
> 2026-09-06, including Holmes, which this runbook previously said to skip. The
> numbers are in `results/axes-table.md`, `results/vs-paper.md` and
> `results/rf-slot-sweep.md`; the figure is `results/axes.png`. Sections below
> have been corrected where they described the CPU-prep code rather than what
> actually ran. Every correction is in `logs/deltas.md`.


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
| `src/models.py` | DF/Tik-Tok and RF architectures, the input transforms and the TAM builder. Table C.1 lives in `run_torch.py`'s `CONFIG` |
| `src/holmes.py`, `src/run_holmes.py` | Holmes: network, TAF and temporal features, and the four-stage pipeline |
| `src/compare_to_paper.py` | Puts our closed-world cells beside the thesis's open-world ones |
| `src/run_torch.py` | The runner. Same 20% holdout protocol and JSON row schema as `run_kfp.py` |
| `src/plot_axes.py` | The deliverable scatter plus `results/axes-table.md`. Reads every `results/*.json`, marks missing cells "not run", and excludes the `rf-n*` sweeps |
| `src/sweep_summary.py` | Writes `results/rf-slot-sweep.md` from the four sweep runs |
| `results/kfp.json` | k-FP, both axes, 3 seeds, run earlier on the laptop |

Commands:

```bash
python track-a-robustness/src/run_torch.py df
python track-a-robustness/src/run_torch.py tiktok
python track-a-robustness/src/run_torch.py rf
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes cross-network --slots 300 --tag rf-n300
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes cross-network --slots 150 --tag rf-n150
python track-a-robustness/src/run_holmes.py --seeds 3
python track-a-robustness/src/plot_axes.py
python track-a-robustness/src/compare_to_paper.py
```

The sweep rebuilds the TAM per slot setting, which takes about 5 s and is
required: under the authors' `(N-1)` binning the 1800-slot matrix does not
aggregate exactly into 300 or 150. `--cells in-dist` restricts evaluation and is
how the gates below were run.

### What actually ran, 2026-09-06

Both gates passed. DF in-distribution 0.9786 against a 0.95 bar; DF
cross-network CA 0.9675, a drop of 0.008, so no collapse. Training is about 45 s
per run, not the single-digit minutes this runbook estimated, because every
input tensor is resident on the GPU for the whole run.

Two corrections to the CPU-prep code were needed before the numbers meant
anything, both in `logs/deltas.md`:

- **DF pooling.** Keras `same` pooling is asymmetric; a symmetric `padding=2`
  flattens to 4,864 instead of the paper's 5,120.
- **RF architecture.** The prep version was an approximation. The RF authors
  released their code, so it is now transcribed from `robust-fingerprinting/RF`,
  including a channel-mixing reshape and a BatchNorm+ReLU before the pooled
  logits. It has no fully connected layer and is slot-agnostic.

### Holmes

**Implemented and run**, reversing the earlier decision. The reason for skipping
it was that Table C.1 is too thin to reimplement faithfully. That is true of the
table and false of the situation: the authors released their complete code as
WFlib (`FIND-Lab/Website-Fingerprinting-Library`, branch `master`), so nothing
had to be guessed.

Table C.1's Holmes column is also misleading. It is not one dual-branch network;
the slash-separated pairs are two *separate models* in a four-stage pipeline:
an auxiliary CNN on a 1000-bin temporal feature (CrossEntropy, Adam, batch 200)
used only to compute DeepLiftShap attributions, which drive a per-class
truncation augmentation, and then the Holmes encoder on TAF (SupConLoss, AdamW,
batch 256), which emits a 128-d embedding with no classifier head and needs a
centroid-and-radius calibration step to predict at all.

Both feature extractors were verified against literal transcriptions of the
authors' own loops on real traces, max absolute difference 0.0.

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

**Holmes ran, and was gated like DF.** The "not run" decision was reversed once
the authors' released code was found (see section 1). It was held to the same
bar DF was: in-distribution macro F1 had to clear 0.95 before any cross-network
or drift number would be reported. It reached 0.9588, so the numbers are real
measurements rather than an approximation, and the point is on the scatter.
Had it missed that bar it would have been reported as not run.

## 4. Runtime, as measured

About 2 hours of GPU time for the whole grid, five classifiers x 3 seeds x 2
axes, plus the four sweep runs.

| Classifier | Per training run | Note |
|---|---|---|
| DF | 40-47 s | 30 epochs |
| Tik-Tok | 47-86 s | batch 32, so 4x the steps; early stopping usually fires at 24-30 |
| RF | 41-42 s | |
| Holmes | ~7.6 min per seed-axis | four stages, and a kNN monitor that re-embeds the memory bank every epoch |

The original estimate of single-digit minutes per run was pessimistic for the
three single-stage models and optimistic for Holmes.

The thing that makes this fast is keeping every input tensor resident on the GPU
for the whole run rather than streaming batches from host memory; the largest
axis needs about 3.4 GiB. Feature construction is built once per collection per
run and held in memory, never per seed: the TAM takes about 5 s per collection
and the TAF about 11 s for the 42k augmented traces. No disk cache is used or
needed. If a single run is taking an hour, something is on the CPU that should
not be.

## 5. Deliverable, done

`src/plot_axes.py` reads every `results/*.json` and draws one point per
classifier, x = cross-network CA macro F1, y = drift month-6 macro F1, error
bars from the 3 seeds. Both axes are labelled closed-world in the figure itself,
because the plot will outlive the caption explaining that it is not the paper's
open-world measurement. Sweep files (`rf-n*.json`) are excluded from the plot
unless `--include-sweeps` is passed.

Output: `results/axes.png`, `results/axes-table.md`, `results/vs-paper.md`,
`results/rf-slot-sweep.md`. The verdict is `docs/track-a-robustness-axes.md`.

The three questions the verdict had to answer, and where they landed:

1. **Do classifiers trade places, or rank the same on both?** They trade places,
   but it rests on RF, which goes fourth of five on network mismatch to first on
   drift, and on k-FP, which slides third to fifth. The other three shift by one
   place. Rank correlation between the axes is 0.20, indistinguishable from
   chance at n = 5, so it is reported as descriptive. The weaker claim, that no
   classifier is good at both, holds cleanly: the smallest worst-case
   degradation is RF's -0.250 and three of five exceed -0.35.
2. **Does the RF slot-size sweep explain its cross-network position away?** No.
   Widening the slot makes RF monotonically worse, not better. A drift arm was
   added as a control, which the thesis does not report, and coarsening damages
   both axes by a similar margin, so slot size is general information loss
   rather than a network-mismatch knob.
3. **What does closed-world scoring cost?** The magnitudes entirely and the
   ordering not at all. Cross-network cells sit 0.318 from the published values
   on average, RF by +0.672, but the rank ordering is reproduced exactly on both
   axes (Spearman 1.000). Since the hypothesis is a claim about ordering it is
   testable closed-world, though this still does not satisfy the brief's step-3
   gate: the drift agreement is corroboration, not reproduction.

k-FP's point, known before the GPU work started, was **(0.797, 0.487)** and is
unchanged.
