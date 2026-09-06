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

Section 4 qualifies this substantially: the network axis as the thesis measures
it is a single country pair, and it is the hardest of the four available, for
every classifier.

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

Two classifiers are hurt *more* by moving country than by ageing six months: RF
(ratio 0.88) and Holmes (0.80), where the ratio is drift damage over network
damage. For the other three, drift dominates, by 39.6x for DF, 13.4x for Tik-Tok
and 2.9x for k-FP. That ordering, not the rank inversion, is the most robust
distinction visible in the data, and it is the reason the stronger claim above
is described as resting on RF's rank inversion rather than on the direction of
the comparison, which two classifiers share.

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

## 4. Is the network axis measuring a classifier, or one country pair?

Added after the fact, and it is the largest qualification in this document.
Full detail in `track-a-robustness/results/netpairs/summary.md`.

The thesis measures network-mismatch robustness at exactly one point, train AU
test CA. Post-Conflux month 0 is the only collection where AU, CA and UK were
gathered together, which allows four ordered pairs from two training vantages.
All five classifiers, 3 seeds. Degradation from each axis's own anchor:

| Classifier | AU->CA | AU->UK | UK->AU | UK->CA |
|---|---|---|---|---|
| DF | −0.070 | −0.011 | −0.010 | −0.052 |
| Tik-Tok | −0.106 | −0.025 | −0.015 | −0.057 |
| k-FP | −0.252 | −0.099 | −0.044 | −0.105 |
| RF | −0.269 | −0.059 | −0.026 | −0.074 |
| Holmes | −0.425 | −0.229 | −0.078 | −0.080 |

Two things follow, and both cut against the strong reading of the main result.

**RF's cross-network collapse is largely specific to AU->CA.** It loses 0.269
there and between 0.026 and 0.074 on the other three pairs, where it is ahead of
k-FP and within a few points of Tik-Tok. That is not the profile of a classifier
that cannot cross networks. RF is second or third worst on every pair and never
the worst, so the dramatic version of the claim rests on the one pair the thesis
reports.

**The training vantage matters roughly three times more than the pair.**
Averaging each classifier's two test cells per vantage, every classifier
degrades more trained on AU than trained on UK, by 1.3x (DF) to 4.2x (Holmes)
and 2.9x on the mean. And AU->CA is the hardest of the four cells for all five
classifiers, unanimously. The thesis's headline cross-network number is
therefore measured at the most pessimistic of the four available configurations,
for every classifier tested.

Median page load time is 15.97 s on AU against 11.99 s on CA and 12.05 s on UK,
so CA and UK are near-identical and AU is about a third slower. Training on the
outlier vantage learns a timing distribution that matches neither of the others,
while training on UK transfers both ways. The asymmetry fits: training on AU and
testing elsewhere is expensive, testing on AU from elsewhere is cheap. That is a
mechanism consistent with the data rather than a demonstrated cause; three
vantages cannot separate load time from everything else that differs between
countries, and the released traces do not record RTT.

**What survives.** RF is still the only classifier whose drift robustness beats
its network robustness, on every pair, so the qualitative trade-off that carries
the two-axis claim is not an artefact of pair choice. What does not survive is
the magnitude. A large part of what the thesis attributes to network-mismatch
robustness is carried by the choice of training vantage, which is a property of
the measurement setup and not of the classifier.

**A confound this exposes in the main result.** The two axes in the main table
are not measured from the same vantage: the cross-network axis trains on AU and
the drift axis trains on UK, following the thesis's own Table 4.1 and Table 4.3.
Given that AU-trained models degrade about 2.9x more in general, the network
axis is measured under a handicap the drift axis does not carry. Some of the
apparent distinctness of the two axes could be a vantage effect rather than an
axis effect, and nothing in this run separates the two.

## What would change this answer

- **The open-world background set.** Every caveat above traces to its absence.
  The DUA request is drafted and unsent in `docs/correspondence/`.
- **More classifiers.** The independence claim rests on n = 5 and on RF in
  particular. Rank correlation of 0.20 is not evidence of independence at that
  sample size; it is the absence of evidence for dependence.
- **RF's seed variance.** At sd 0.0217 on the cell that carries the argument,
  three seeds is thin. Ten would be cheap, about 7 minutes.
- ~~**A second network pair.**~~ Done, see section 4, and it mattered more than
  expected: the training vantage carries about 3x more of the effect than the
  pair does.
- **Both axes from one vantage.** The largest open confound. The network axis
  trains on AU and the drift axis on UK, so vantage and axis are entangled. The
  archive holds `post-month6-cfx0-au`, which would allow an AU-trained drift
  cell and a genuinely like-for-like scatter. About an hour.

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
# the four-pair comparison in section 4
for m in df tiktok rf; do python track-a-robustness/src/run_torch.py $m --seeds 3 \
  --axes cross-network-post-au cross-network-post-uk --tag netpairs/$m; done
python track-a-robustness/src/run_kfp.py 3 --axes cross-network-post-au cross-network-post-uk --tag netpairs/kfp
python track-a-robustness/src/run_holmes.py --seeds 3 --axes cross-network-post-au cross-network-post-uk --tag netpairs/holmes
python track-a-robustness/src/netpair_summary.py
```

About 2 hours of GPU time end to end, dominated by Holmes at roughly 7.6 minutes
per seed-axis for its four-stage pipeline. k-FP is CPU-only and ran on the laptop.
