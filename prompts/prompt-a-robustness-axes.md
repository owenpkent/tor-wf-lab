# Prompt A: robustness axes (aim for a result)

> Verbatim as given. Do not edit; record deviations in `track-a-robustness/logs/deltas.md`.

Reference for both: Shadbeh, Khajavi, Wang, "Reality Check for Tor Website
Fingerprinting in the Open World", arXiv:2603.07412. Code and data at
https://osf.io/9m8ea/ (synthetic monitored traces open; real non-monitored set
behind a data use agreement).

I want to characterize a gap identified in arXiv:2603.07412: robustness to
network mismatch and robustness to temporal drift appear to be distinct
properties, and no current WF classifier is good at both. In their Table 3, RF
scores F1 0.046 under cross-network training (train AU, test CA) but is the
best model under six-month concept drift (Table 5, F1 0.754). DF is the
reverse: F1 0.939 cross-network, 0.685 after six months.

Goal for this session: reproduce the two-axis picture on data I can actually
get, and produce a single plot placing each classifier on both axes.

Environment: single RTX 5090, Linux. Assume no network access to restricted
datasets unless I tell you otherwise.

## Steps

1. Pull the OSF repository at https://osf.io/9m8ea/ and inventory what is
   openly downloadable versus DUA-gated. Report this before doing anything
   else. If the synthetic monitored traces alone are not enough to run both
   axes, say so and propose the closest feasible substitute rather than
   quietly proceeding.
2. Get their code running for k-FP, DF, Tik-Tok, RF and Holmes. Hyperparameters
   are in their Appendix A Table 7. Do not retune; the point is to compare
   published configurations.
3. Reproduce one number from their paper as a sanity check before running
   anything new. Tell me which number you picked and how close you got. If you
   cannot get within a few points, stop and report rather than continuing.
4. Run the two axes with at least three seeds each, and report variance. Single
   run numbers are what makes most of this literature hard to compare.
5. Produce one scatter plot: cross-network F1 on one axis, six-month (or
   longest available gap) F1 on the other, one point per classifier with error
   bars.

## Constraints

- Do not invent numbers. If a run fails or data is missing, say so plainly in
  the writeup.
- Note explicitly which of their results you could reproduce and which you
  could not, and why.
- Keep a short log of what changed between their setup and yours.

## Deliverable

The plot, a table of the underlying numbers with seeds and variance, and a
paragraph on whether the two-axis gap holds up under the data I could access.
