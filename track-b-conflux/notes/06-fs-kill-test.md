# Track B kill test: does latency advantage buy the first segment?

Run 2026-09-06 on the laptop, no simulator, no DUA. Code in `../src/`, raw
numbers in `../results/fs-sweep.json`, figure `../results/fs-rate.png`.
Reproduce with `.venv/bin/python track-b-conflux/src/run_fs_sweep.py`.

Detector: the paper's three guard-side rules (thesis 4.3.2), reimplemented in
`src/fs_detector.py`. Data: the open `post-month2-cfx2-ca*` files, sha512
verified.

## Result: the mechanism is real

| Guard advantage | n | FS rate | Median cells: all / FS legs / other legs |
|---|---|---|---|
| 0 ms | 34,626 | **0.448** | 1436 / 1602 / 1300 |
| 32 ms | 18,293 | 0.568 | 1717 / 1852 / 1525 |
| 64 ms | 18,673 | 0.675 | 1808 / 1912 / 1589 |
| 128 ms | 19,748 | **0.891** | 2081 / 2124 / 1750 |
| 256 ms | 20,840 | 0.961 | 2486 / 2507 / 1945 |
| 512 ms | 18,853 | 0.977 | 2947 / 2967 / 2054 |

Monotone, steepest between 64 and 128 ms, saturated past 256 ms. The knee sits
where the paper's TPR curve has its knee, at the same place as the roughly
150 ms inter-client latency delta.

## Controls

| Set | FS rate | Reading |
|---|---|---|
| cfx0 CA month 0 | **1.0000** | Detector sanity: with Conflux off there is one leg per load and every trace must be a first segment. It is, on 22,496 traces, with no exceptions. |
| cfx0 UK month 2 | 1.0000 | Same, different site and month. |
| cfx2 AU month 2 | 0.211 | Same guard, no manipulation, a client further away. |
| cfx2 UK month 2 | 0.151 | Same. |

The AU and UK numbers matter more than they look. They are the same effect
occurring naturally: when the guard is *not* the low-latency leg it loses the
first segment four times out of five, with nobody manipulating anything. The
sweep is a controlled version of a bias that is already there.

## Independent corroboration of the paper

The thesis says approximately 65% of monitored traces under Conflux contain less
than half the full page load. Taking the cfx0 CA median of 4,542 cells as a full
load, the measured fraction below half at 0 ms advantage is **0.659**. That is a
number we did not aim at, arrived at from the open files alone, and it lands on
their figure.

## The finding that changes the project's scope

FS ownership is not the whole attack. Assume, as the paper implies, that non-FS
traces contribute roughly nothing to detection. Then the paper's DF TPR at
FPR 0.5% decomposes:

| Advantage | TPR (theirs) | FS rate (ours) | Implied TPR given FS |
|---|---|---|---|
| 0 ms | 0.189 | 0.448 | 0.42 |
| 128 ms | 0.736 | 0.891 | 0.83 |

The conditional term doubles too. Owning the first segment is worth twice as
much at 128 ms as at 0 ms, because the advantaged leg also carries more of the
load once it has won: median cells on FS legs go 1,602 to 2,124, and the share
of FS traces holding less than half a load falls from 0.62 to 0.39.

**So a policy that only randomizes first-segment ownership addresses one of two
multiplicative factors.** Under this crude model, restoring FS rate to 0.448 at
a 128 ms advantage would take TPR from 0.736 to about 0.37, not back to 0.189.
Getting the rest requires limiting how much of the tail the advantaged leg
carries, which is the LowRTT "keep the fast leg until it blocks" behaviour, not
the first-leg pick. Candidate B in `03-candidate-policies.md` touches both;
candidate A touches only the first.

Caveat: their TPR is open-world at a fixed FPR over a slightly different
population than our per-file FS rate, and the "non-FS contributes nothing"
assumption is theirs, not something we measured. Treat the decomposition as an
order-of-magnitude argument for where to aim, not a result.

## Detector robustness

The rules assume the trace begins where the Conflux handshake ends. Running the
detector at assumed offsets 0 through 4 gives 0.448 / 0.024 / 0.321 / 0.300 /
0.047 at 0 ms advantage. Offset 0 is clearly the right alignment: rule 1 wants
an outgoing first cell, and the released traces open with the `+-++` BEGIN
pattern, so any odd offset collapses. The absolute rate is therefore alignment
dependent, but the trend is not: at offsets 2 and 3 the sweep still climbs
monotonically, 0.32 to 0.68 and 0.30 to 0.68. The conclusion survives the
assumption being wrong; only the exact numbers would move.
