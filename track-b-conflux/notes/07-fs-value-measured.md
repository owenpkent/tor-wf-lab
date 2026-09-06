# What first-segment ownership is actually worth

Run 2026-09-06, same day as the kill test. Code `../src/run_fs_kfp.py`, numbers
`../results/fs-kfp.json`, figure `../results/fs-kfp.png`.

`06-fs-kill-test.md` measured how *often* a latency-advantaged guard owns the
first segment, then inferred what owning it is worth from the paper's TPR. This
measures the second half instead of inferring it.

Design: for each latency setting, train k-FP on a stratified 80% of that
collection, mixed exactly as an attacker would collect it, then score the
held-out 20% separately on its FS and non-FS traces. 107 classes common to all
six conditions, 3 seeds, RF with 1,000 trees as in Table C.1. Chance is 0.009.

## Result

| Advantage | FS rate | Accuracy, all | Accuracy given FS | Accuracy given non-FS | Ratio | Non-FS test traces |
|---|---|---|---|---|---|---|
| 0 ms | 0.448 | 0.5399 | 0.7441 | 0.3740 | 1.99 | 3,780 |
| 32 ms | 0.561 | 0.6225 | 0.7924 | 0.4051 | 1.96 | 1,605 |
| 64 ms | 0.674 | 0.6860 | 0.8297 | 0.3882 | 2.14 | 1,216 |
| 128 ms | 0.884 | 0.8217 | 0.8862 | 0.3283 | 2.70 | 456 |
| 256 ms | 0.961 | 0.8786 | 0.9039 | 0.2592 | 3.49 | 163 |
| 512 ms | 0.977 | 0.8911 | 0.9067 | 0.2360 | 3.84 | 87 |

Seed spread is 0.001 to 0.005 except the last non-FS cell, which is 0.046 on 87
traces. `fs_rate * acc_fs + (1 - fs_rate) * acc_nonfs` reproduces `acc_all` to
four decimals at every setting, as it must.

## The finding: ownership dominates, enrichment is second order

Growth from the no-advantage baseline:

| Advantage | FS rate | Accuracy given FS | Overall accuracy |
|---|---|---|---|
| 128 ms | **x1.97** | **x1.19** | x1.52 |
| 512 ms | x2.18 | x1.22 | x1.65 |

A guard that buys 128 ms of latency advantage roughly doubles how often it owns
the start of the page load, and improves its accuracy on the traces it does own
by about a fifth. The first term is the attack.

## This corrects the inference in note 06

Note 06 combined the paper's DF TPR with our FS rate and, assuming non-FS traces
contribute nothing, inferred that detection given first-segment ownership
doubles from 0.42 to 0.83. Measured directly, it rises by 19%, not 100%.

The assumption is what broke. **Non-FS traces are not worthless**: k-FP gets
0.374 of them right with no advantage at all, forty times chance. The traces a
guard sees when it loses the first segment are still highly identifiable in a
closed world. Anything derived from "non-FS contributes nothing" should be
treated as unsound, including the earlier claim that candidate A alone would
only take TPR from 0.736 to about 0.37.

Two caveats in the other direction, so this does not get over-read:

- **Closed-world accuracy is not open-world TPR at a fixed 0.5% FPR.** Seeing
  more of a load mostly buys precision, and precision is exactly what a
  closed-world metric cannot see. The enrichment term could be materially larger
  in the open world, where the paper's numbers live. This measurement bounds the
  effect in the world we can access, and no further.
- **The non-FS column thins out fast.** At 512 ms it rests on 87 traces, and the
  training mix has shifted to 98% FS by then, so the model is barely fitted to
  non-FS traffic. The declining non-FS curve is probably that shift rather than
  the traces getting less informative, and the trace lengths agree: non-FS
  median cells *rise* over the sweep, 1,330 to 2,017.

## Consequence for the candidate policies

Candidate A, randomizing the initial leg, is back in contention as a standalone
measure: it attacks the dominant term directly. Note 06 demoted it on the
strength of a decomposition that has now been measured and did not hold.

Candidate B, CWNDRTT over the first segment, is still the better design, but for
a different reason than note 06 gave. Its advantage is not that it also
suppresses a large enrichment term; it is that thinning the prefix degrades the
features on the traces the guard *does* own, which is the 0.744 baseline that
randomization alone leaves untouched.

The experiment that would settle it, and which this harness now supports: apply
each candidate policy's leg assignment to these traces offline and rerun this
same measurement.
