# Track A: robustness axes

Brief: `../prompts/prompt-a-robustness-axes.md`. Verdict:
`../docs/track-a-robustness-axes.md`.

Hypothesis under test: network-mismatch robustness and temporal-drift
robustness are distinct properties, and no current WF classifier has both.
Classifiers in scope: k-FP, DF, Tik-Tok, RF, Holmes. All five ran.

**Outcome.** No classifier is good at both axes, so the hypothesis holds in its
weaker form. The stronger form does not survive intact. *Which* axis costs a
classifier more turns out to be set by the training vantage rather than by the
classifier: of the four vantage-and-target cells, only AU->CA is network-limited
for anyone, and there for two of five (RF and Holmes, not RF alone as the first
draft of this file said). What is invariant is the **ordering** by network
sensitivity relative to drift damage, RF < k-FP < Tik-Tok < DF, identical in all
four cells and across four country pairs, but that covers four of the five:
Holmes takes a different place in each cell. Full argument in the verdict,
sections 4 and 5.

## Gate order, from the brief, and where each landed

1. **OSF inventory.** Done. ~10.6 GB of monitored traces are open and span
   AU/CA/UK across months 0/2/6; the open-world background set is DUA-gated and
   not even listed. Both axes are runnable closed-world only.
   `logs/osf-inventory.md`.
2. **Their code running, published hyperparameters only.** Partly unsatisfiable.
   The thesis authors released nothing, so this is a five-classifier
   reimplementation. Hyperparameters are Table C.1 verbatim and untuned.
   Architectures come from each classifier's own paper, and where those authors
   released code it was transcribed rather than reconstructed: RF from
   `robust-fingerprinting/RF`, Holmes from WFlib.
3. **Reproduce one paper number.** **Not satisfied, and cannot be on open data.**
   Every number here is closed-world macro F1; every number in their tables is
   open-world F1 from a tuned threshold against the background set. Different
   measurements. The drift column nonetheless lands a mean absolute 0.008 from
   the published month-2 values, worst cell 0.018, and the rank ordering on both
   axes matches theirs exactly, but that is corroboration and must not be quoted
   as reproduction.
   `results/vs-paper.md`.
4. **Both axes, 3+ seeds, variance reported.** Done, 3 seeds, 315 result rows
   across 24 files, plus 3 rows in the two `results/scratch/` gate checks.
   `results/axes-table.md`. Seed variance is not uniform: RF's
   cross-network cell has sd 0.0217 against DF's 0.0021 on the same cell.
5. **One scatter plot.** Done, `results/axes.png`, five points with error bars,
   both axes labelled closed-world in the figure itself. Read it for the
   *relative* positions only: section 5 of the verdict shows a classifier's
   absolute coordinates move with the training vantage.

Steps 1 and 3 were the real gates, and step 3 is the one that failed. It failed
in the way step 1 predicted it would, which is why the run proceeded: the
two-axis question is a claim about ordering, and ordering survives closed-world
scoring even though the cell values do not.

## Layout

```
src/     fetch and verify, loaders, the five classifiers, the runners, the plot
data/    OSF traces, gitignored, 8 collections and 3.2 GB
results/ per-classifier JSON, the generated tables, the figure
  netpairs/    four country pairs, section 4 of the verdict
  vantage/     both axes from the AU vantage, plus the generated summary
  vantage-uk/  the same test from the UK vantage, section 5
  scratch/     the two runbook gate checks, not part of the deliverable counts
logs/    deltas.md (every deviation), paper-numbers.md, osf-inventory.md,
         holmes-attr-coverage.md (which classes Holmes could not attribute)
RUNBOOK-5090.md   what was run on the GPU box, and what it cost
```

Commands for every result are in `RUNBOOK-5090.md` section 1.
