# Track A: the paper's numbers, checked against the PDF

Closes README open item 1. Date 2026-09-06. Source: the SFU thesis version,
`https://summit.sfu.ca/_flysystem/fedora/2026-04/etd24263.pdf`, 1,109,240 bytes,
HTTP 200, no login. Text extracted with `pdftotext -layout`. The arXiv version
was not re-checked; the thesis is the version that carries Appendix C.

## Table numbering

The brief cites the arXiv numbering. The thesis numbers the same tables
differently, and everything below is quoted from the thesis.

| Brief | Thesis | Content |
|---|---|---|
| Table 3 | Table 4.1 | Open-world at the guard, pre-Conflux, cross-network and pooled |
| Table 5 | Table 4.3 | Concept drift, month 0 / 2 / 6 |
| Appendix A Table 7 | Appendix C Table C.1 | Hyperparameters |
| (not cited) | Table 4.2 | Same as 4.1 without the guard advantage |
| (not cited) | Table 4.4 | Under Conflux, single-leg guard |

## The seven claims

All seven match the thesis exactly. No transcription error in the brief.

| Claim in README | Value | Found in | Verdict |
|---|---|---|---|
| Best attack, real open world, 9% base rate | 0.956 / 0.922 | Table 4.1, DF, Train AU / Test CA | ✅ exact |
| RF cross-network F1 | 0.046 | Table 4.1, RF | ✅ exact |
| RF six-month drift F1 | 0.754 | Table 4.3, RF month 6 | ✅ exact |
| DF cross-network F1 | 0.939 | Table 4.1, DF | ✅ exact |
| DF six-month drift F1 | 0.685 | Table 4.3, DF month 6 | ✅ exact |
| DF under Conflux, one leg | 0.939 -> 0.379 | Table 4.4, DF, Train AU / Test CA | ✅ exact |
| DF, 128 ms guard advantage | TPR 0.189 -> 0.736 | Section 4.3.1 body text, p.38 | ✅ exact |

"Precision" in the first row is π10, r-precision at r = 10, i.e. ten times as
much unmonitored as monitored traffic, a 9.1% base rate. Every F1 in these
tables is derived from π10 and recall at a threshold chosen per model to
maximize F1.

## Table 4.1 and Table 4.3 in full

Table 4.1, open-world at the guard, pre-Conflux dataset:

| Classifier | Baseline π10 / R / F1 | Train AU, test CA | Pooled |
|---|---|---|---|
| k-FP (2016) | 0.861 / 0.791 / 0.825 | 0.717 / 0.307 / 0.430 | 0.970 / 0.915 / 0.942 |
| DF (2018) | 0.951 / 0.940 / 0.945 | 0.956 / 0.922 / 0.939 | 0.979 / 0.966 / 0.973 |
| Tik-Tok (2019) | 0.947 / 0.896 / 0.921 | 0.901 / 0.844 / 0.872 | 0.980 / 0.948 / 0.964 |
| RF (2023) | 0.969 / 0.958 / 0.964 | 0.089 / 0.031 / 0.046 | 0.980 / 0.968 / 0.974 |
| Holmes (2024) | 0.970 / 0.931 / 0.950 | 0.176 / 0.004 / 0.009 | 0.950 / 0.956 / 0.953 |

Table 4.3, concept drift, F1 only:

| Classifier | Month 0 | Month 2 | Month 6 |
|---|---|---|---|
| k-FP | 0.926 | 0.761 | 0.547 |
| DF | 0.967 | 0.854 | 0.685 |
| Tik-Tok | 0.956 | 0.827 | 0.653 |
| RF | 0.972 | 0.907 | 0.754 |
| Holmes | 0.966 | 0.740 | 0.622 |

## Three things the brief does not say, and they change the run

1. **The drift study is the UK client, not AU or CA.** Section 4.2.9: "a
   longitudinal study using our UK client", trained on month 0 and evaluated on
   the later collections from the same vantage point. The open OSF files support
   this exactly: `post-month{0,2,6}-cfx0-uk.npz`. The AU and CA clients have no
   month-2 cfx0 file, so UK is also the only site where the full 0/2/6 curve is
   constructible.
2. **The cross-network table is the pre-Conflux dataset.** So the cross-network
   axis is `pre-conflux/pre-month0-cfx0-{au,ca}.npz`, not the post-Conflux
   cfx0 files. The two axes therefore draw on different collections, which is
   the authors' design, not an artifact of ours.
3. **RF is a 2D CNN over a Traffic Aggregation Matrix, not a random forest.**
   Table C.1 gives Model Type = 2D CNN, TAM length 1800, Adam, batch 200, 30
   epochs. This corrects `osf-inventory.md`, which said "RF is sklearn". Only
   k-FP is a random forest. It matters for scheduling: four of the five
   classifiers need a GPU, not three.

## Hyperparameters, Table C.1, verbatim

| | k-FP | DF | Tik-Tok | RF | Holmes |
|---|---|---|---|---|---|
| Model | Random Forest | 1D CNN | 1D CNN | 2D CNN | Dual-branch CNN |
| Batch | N/A | 128 | 32 | 200 | 200 / 256 |
| Epochs | N/A | 30 | 30 max | 30 | 30 |
| Optimizer | N/A | Adamax | Adamax | Adam | Adam / AdamW |
| LR | N/A | 0.002 | 0.002 | 5e-4 x 0.2^(epoch/30) | 0.0005 |
| Loss | N/A | CrossEntropy | CrossEntropy | CrossEntropy | CrossEntropy / SupConLoss |
| Input | 175 features (max) | length 5,000 | length 5,000 | TAM length 1800 | temporal 1000 / TAF 2000 |
| Other | n_est = 1000, feature importances used | β1 0.9 β2 0.999 ε 1e-8 | same, early stop on val_loss patience 6 | max load time set per experiment, 42-47 s, else default 80 s | best-F1 epoch selection |

## Appendix C.1, and why it matters for the verdict

The authors explain RF's cross-network collapse mechanically. TAM slot duration
is Tmax / N; at the default 80 s / 1800 that is roughly 44 ms, well under the
approximately 150 ms RTT difference between the AU training client and the CA
test client. Recall at the default slot size is about 0.01. Widening the slot
past the latency delta lifts TPR to about 0.18 at 150 ms and a maximum of about
0.19 at 300 ms, still far below DF's roughly 0.94.

Track A's verdict paragraph has to engage with this. RF's failure on the
network-mismatch axis is a documented sensitivity of one preprocessing constant
to an unmodelled latency shift, and the authors already showed that retuning it
recovers only a fraction of the gap. That is weaker than "the two axes are
intrinsically distinct properties", and it is the obvious counter-reading of the
two-axis claim.
