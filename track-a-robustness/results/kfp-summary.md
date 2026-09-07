# k-FP, closed world, both axes

Run 2026-09-06 on the Linux laptop (no GPU needed for this classifier).
Raw per-seed rows in `kfp.json`. Reproduce with
`.venv/bin/python track-a-robustness/src/run_kfp.py`.

Random forest, n_estimators = 1000 per thesis Table C.1, 175-dimensional
feature vector, 3 seeds. `in-dist` is a 20% stratified holdout of the training
collection, resampled per seed. Mean +/- sd over seeds.

| Axis | Cell | Train | Test | Classes | Macro F1 | Accuracy |
|---|---|---|---|---|---|---|
| cross-network | in-dist (AU) | 16,528 | 4,132 | 103 | 0.9582 +/- 0.0041 | 0.9578 +/- 0.0041 |
| cross-network | CA | 16,528 | 21,068 | 103 | 0.7973 +/- 0.0036 | 0.8043 +/- 0.0037 |
| drift | in-dist (UK m0) | 16,619 | 4,155 | 106 | 0.9500 +/- 0.0011 | 0.9496 +/- 0.0011 |
| drift | UK month 2 | 16,619 | 21,164 | 106 | 0.7620 +/- 0.0018 | 0.7916 +/- 0.0010 |
| drift | UK month 6 | 16,619 | 20,664 | 106 | 0.4874 +/- 0.0013 | 0.5378 +/- 0.0014 |

Degradation from the in-distribution anchor: **-0.161 macro F1** across the
network, **-0.188** at two months, **-0.463** at six months.

Seed variance is tiny, of order 0.004 at most. For k-FP the single-run numbers
the brief complains about are not the problem; whatever noise exists in this
literature is not coming from the forest's random state. Worth re-checking once
the CNNs run, where seed variance is normally much larger.

**Checked, and the expectation was wrong.** The CNNs are mostly *steadier* than
k-FP, not noisier: DF's cross-network cell has sd 0.0021 against k-FP's 0.0036.
The exception is RF at sd 0.0217, an order of magnitude above the rest and on
exactly the cell the two-axis argument leans on. See `axes-table.md`.

## Against the paper: do not read this as a reproduction

Their k-FP row is open-world F1 derived from π10 at a tuned threshold. Ours is
closed-world macro F1 over the monitored classes. Different measurements.

| Cell | Theirs (open world) | Ours (closed world) |
|---|---|---|
| Cross-network, train AU test CA | 0.430 | 0.7973 |
| Drift month 0 | 0.926 | 0.9500 (in-dist holdout) |
| Drift month 2 | 0.761 | 0.7620 |
| Drift month 6 | 0.547 | 0.4874 |

The drift column lines up closely and the cross-network cell does not, which is
the pattern you would predict: removing the background set costs a classifier
nothing on a drift comparison where both sides shift together, and flatters it
heavily where the failure mode was false positives against background traffic.
The month-2 agreement to three decimals is a coincidence and should not be
quoted as anything else.

Brief step 3 asks for one reproduced paper number as a gate. **That gate cannot
be passed on open data.** Nothing here is the same measurement as anything in
their tables, so the honest report is that step 3 is unsatisfiable closed-world,
not that it passed.

## Caveat on the six-month number

Six of the 112 sites are absent from the UK month-6 collection and are excluded
from all cells of that axis by the label intersection. That controls for the
missing classes but not for partial attrition: a site that still exists but now
serves half as many pages is still in the label set and still counts against
recall. Some of the -0.463 is the web changing rather than the classifier aging,
and the paper does not separate these either.
