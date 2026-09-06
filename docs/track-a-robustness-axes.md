# Track A: are network-mismatch and temporal-drift robustness distinct axes?

Against Shadbeh, Khajavi & Wang, *Reality Check for Tor Website Fingerprinting
in the Open World* (arXiv:2603.07412). Brief: `prompts/prompt-a-robustness-axes.md`.

Five classifiers, both axes, 3 seeds each, closed world, run on an RTX 5090 on
2026-09-06. Numbers: `track-a-robustness/results/axes-table.md`. Figure:
`results/axes.png`. Slot-size sweep: `results/rf-slot-sweep.md`. Comparison to
the published tables: `results/vs-paper.md`. Every deviation from the published
configurations: `track-a-robustness/logs/deltas.md`.

## The answer

**The hypothesis holds: no classifier is good at both.** Every one of the five
loses heavily on at least one axis, and the two best are best at different
things. DF is the strongest against network mismatch (0.968) and gives up 0.331
to six months of drift. RF is the strongest against drift (0.748) and gives up
0.250 across networks. Nothing sits in the top-right of the scatter.

**The stronger claim, that the two axes are genuinely independent properties, is
carried almost entirely by RF.** Three of the five classifiers rank identically
on both axes (DF > Tik-Tok, with k-FP below them). RF is the one that inverts,
going from fourth of five on network mismatch to first on drift, and k-FP slides
from third to last. Rank correlation between the axes is 0.20 across five
classifiers, but with n = 5 that is indistinguishable from chance (p = 0.75), so
it is a description of these five points and not an inference about classifiers
in general.

## What ran, and what was checked before it ran

| | |
|---|---|
| GPU | RTX 5090, driver 610.88, torch 2.11.0+cu128, capability `(12, 0)`, `sm_120` present |
| Data | 5 OSF collections, ~1.9 GB, extracted from the bulk archive, all 5 sha512-verified against the authors' lists |
| Protocol | 20% stratified in-distribution holdout per seed, seeds 0/1/2, identical 16,528 / 4,132 split for every classifier |
| World | Closed. The open-world background set is DUA-gated and absent |

Two gates from the runbook, both passed before anything else ran. DF
in-distribution reached **0.9786** against a 0.95 bar, and DF cross-network
reached **0.9675**, a drop of 0.008, confirming that DF survives network
mismatch rather than collapsing. Holmes was held to the same in-distribution bar
and reached 0.9588.

Architectures come from each classifier's own authors, not from the thesis,
which publishes none. Where those authors released code it was transcribed
rather than reconstructed: RF from `robust-fingerprinting/RF`, Holmes from
WFlib. Both Holmes feature extractors were verified against literal
transcriptions of the authors' own loops on real traces, maximum absolute
difference **0.0**.

## The numbers

Closed-world macro F1, mean ± sd over 3 seeds.

| Classifier | cross-network CA | drift month 6 | Δ network | Δ drift |
|---|---|---|---|---|
| DF | **0.9675 ± 0.0021** | 0.6469 ± 0.0139 | −0.008 | −0.331 |
| Tik-Tok | 0.9481 ± 0.0048 | 0.6217 ± 0.0072 | −0.026 | −0.353 |
| k-FP | 0.7973 ± 0.0036 | 0.4874 ± 0.0013 | −0.161 | −0.463 |
| RF | 0.7179 ± 0.0217 | **0.7481 ± 0.0069** | −0.250 | −0.221 |
| Holmes | 0.4529 ± 0.0047 | 0.5739 ± 0.0120 | −0.504 | −0.403 |

Δ is measured against that axis's own in-distribution anchor, so it reads as
degradation rather than as an absolute score.

Seed variance is small but not uniform. RF's cross-network cell has sd 0.0217,
roughly ten times DF's 0.0021 on the same cell. The brief's complaint about
single-run numbers is therefore well founded for exactly the classifier the
two-axis argument depends on: a single RF run could have landed anywhere between
0.688 and 0.737.

## 1. Do classifiers trade places, or simply rank the same on both?

They trade places, but the effect rests on two classifiers moving in opposite
directions rather than on a general pattern.

| Classifier | rank, network | rank, drift |
|---|---|---|
| DF | 1 | 2 |
| Tik-Tok | 2 | 3 |
| k-FP | 3 | 5 |
| RF | 4 | 1 |
| Holmes | 5 | 4 |

RF moves from fourth to first, k-FP from third to fifth. The other three shift
by one place, which is what you would expect from a single underlying quality
ordering with two exceptions layered on top.

The weaker form of the hypothesis is nonetheless clearly supported. Taking each
classifier's *worse* axis, no classifier keeps more than it loses: the smallest
worst-case degradation belongs to RF at −0.250, and three of the five exceed
−0.35. There is no classifier in this set that is simultaneously robust to both
perturbations, which is what the brief asked.

RF is also the only classifier that is hurt *more* by moving country than by
ageing six months. For DF, Tik-Tok and k-FP, drift is 41x, 14x and 2.9x
more damaging than network mismatch respectively. That asymmetry, not the rank inversion, is
the most robust distinction visible in the data.

## 2. Does the RF slot-size sweep explain its cross-network position away?

**No, and the drift arm rules it out.** Full detail in `results/rf-slot-sweep.md`.

Appendix C.1 argues that RF's cross-network collapse is mechanical: the TAM slot
is far shorter than the ~150 ms RTT difference between the AU and CA clients, so
widening it past that delta should recover accuracy. Reproducing that sweep
closed-world gives the opposite result on both axes.

| Slot | cross-network CA | Δ | drift month 6 | Δ |
|---|---|---|---|---|
| 25.0 ms (N=1800) | 0.7179 | −0.250 | 0.7481 | −0.221 |
| 150.5 ms (N=300) | 0.6206 | −0.344 | 0.6179 | −0.335 |
| 302.0 ms (N=150) | 0.5564 | −0.398 | 0.5642 | −0.362 |

Coarsening the slot makes RF monotonically worse, and by a similar margin on
both axes. The drift arm, which the thesis does not report, is the control that
makes this conclusive: if slot duration were specifically a network-mismatch
knob, coarsening it would damage the cross-network cell and leave drift alone.
It damages both, so slot size is a general information-loss parameter, and RF's
distinctive profile survives every setting of it.

This does not contradict the thesis. Their sweep is open-world recall at a tuned
threshold, starting from a near-total collapse of about 0.01; the failure it
repairs is false positives against background traffic, which closed-world
scoring removes by construction. Ours starts from 0.718, where there is no such
failure left to repair. But the counter-reading it invites, that the two-axis
claim is really a statement about one preprocessing constant, is not supported
here: RF's network weakness is worst at exactly the setting the remedy
recommends, and its drift advantage appears at the same fine slot where it is
weakest across networks.

## 3. What does closed-world scoring cost the comparison?

It costs the magnitudes entirely and the ordering not at all, and that
distinction is what makes the verdict survivable.

Mean absolute difference from the published values (`results/vs-paper.md`):

- cross-network: **0.318**
- drift month 2: **0.008**
- drift month 6: **0.037**

The drift axis lands almost exactly on the thesis's numbers across all five
classifiers, despite being a different measurement. The cross-network axis does
not, and the classifiers that move most are RF (+0.672), Holmes (+0.444) and
k-FP (+0.367): precisely the three that carry the two-axis claim. Taken alone
that is fatal, and it is what the brief anticipated when it warned that the gap
between the two worlds is larger than the gaps being compared.

What rescues it is that the **rank ordering is reproduced exactly on both axes**:

| | order |
|---|---|
| Cross-network, thesis | DF > Tik-Tok > k-FP > RF > Holmes |
| Cross-network, ours | DF > Tik-Tok > k-FP > RF > Holmes |
| Drift month 6, thesis | RF > DF > Tik-Tok > Holmes > k-FP |
| Drift month 6, ours | RF > DF > Tik-Tok > Holmes > k-FP |

Spearman correlation with the published values is 1.000 on both axes. An exact
match of a five-way ordering has probability 1/120 under a random permutation,
and it happens on both axes independently. Closed-world scoring compresses the
range and flatters the classifiers whose open-world failure was false positives,
but it does not reshuffle who is good at what.

Since the two-axis hypothesis is a claim about *ordering* rather than about
absolute F1, it is testable closed-world even though the cell values are not
comparable. That is the single most useful thing this run establishes.

It does not, however, satisfy the brief's step-3 gate. Nothing here is the same
measurement as anything in the thesis's tables, so the drift agreement is
corroboration, not reproduction, and should never be quoted as the latter.

## What would change this answer

- **The open-world background set.** Every caveat above traces to its absence.
  The DUA request is drafted and unsent in `docs/correspondence/`.
- **More classifiers.** The independence claim rests on n = 5 and on RF in
  particular. Rank correlation of 0.20 is not evidence of independence at that
  sample size; it is the absence of evidence for dependence.
- **RF's seed variance.** At sd 0.0217 on the cell that carries the argument,
  three seeds is thin. Ten would be cheap, about 7 minutes.
- **A second network pair.** The cross-network axis is one AU→CA comparison. Its
  ~150 ms latency delta is a single point in a space the thesis treats as
  representative.

## Reproducing

```bash
python track-a-robustness/src/run_kfp.py
python track-a-robustness/src/run_torch.py df
python track-a-robustness/src/run_torch.py tiktok
python track-a-robustness/src/run_torch.py rf
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes cross-network --slots 300 --tag rf-n300
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes cross-network --slots 150 --tag rf-n150
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes drift --slots 300 --tag rf-n300-drift
python track-a-robustness/src/run_torch.py rf --seeds 3 --axes drift --slots 150 --tag rf-n150-drift
python track-a-robustness/src/run_holmes.py --seeds 3
python track-a-robustness/src/plot_axes.py
python track-a-robustness/src/compare_to_paper.py
python track-a-robustness/src/sweep_summary.py
```

About 2 hours of GPU time end to end, dominated by Holmes at roughly 7.6 minutes
per seed-axis for its four-stage pipeline. k-FP is CPU-only and ran on the laptop.
