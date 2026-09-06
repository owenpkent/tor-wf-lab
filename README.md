# tor-wf-lab

Two scoped weekend investigations against Shadbeh, Khajavi & Wang, *Reality
Check for Tor Website Fingerprinting in the Open World* (arXiv:2603.07412,
March 2026).

They are independent. Track A aims at an experimental result, Track B aims at a
go/no-go decision. Neither is started yet.

| Track | Question | Deliverable | Status |
|---|---|---|---|
| A | Are network-mismatch robustness and temporal-drift robustness genuinely distinct axes, with no classifier good at both? | Scatter plot + numbers table + verdict paragraph | Step 1 done, blocked on scope decision |
| B | Is "Conflux scheduling that mitigates LowRTT latency bias" a viable multi-week project? | Memo with go/no-go | Not started |

## Layout

```
prompts/                    the two briefs, verbatim, treated as read-only
track-a-robustness/
  src/                      harness around the authors' code
  results/                  numbers tables, the plot
  logs/deltas.md            every difference between their setup and ours
track-b-conflux/notes/      reading notes feeding the memo
docs/                       finished writeups (plot + table for A, memo for B)
```

## Reference material

- Paper: https://arxiv.org/abs/2603.07412
- Full text incl. Appendix A Table 7 (hyperparameters, needed by Track A step 2):
  SFU thesis version, freely downloadable,
  https://summit.sfu.ca/_flysystem/fedora/2026-04/etd24263.pdf
- Code and data: https://osf.io/9m8ea/
  Synthetic monitored traces are open. The real non-monitored (open-world
  background) set is behind a data use agreement.
- Tor proposal 329 (Track B): https://spec.torproject.org/proposals/329-traffic-splitting.html

Verified 2026-09-06: the paper, both mirrors and the arXiv identifier are real.

## Numbers from the paper this repo is trying to interrogate

Recorded here so a later run can be checked against them rather than against
memory. All quoted from the two briefs, not yet independently confirmed against
the PDF.

| Claim | Value |
|---|---|
| Best attack, real open world, 9% base rate | precision 0.956, recall 0.922 |
| RF, cross-network (train AU, test CA), Table 3 | F1 0.046 |
| RF, six-month concept drift, Table 5 | F1 0.754 |
| DF, cross-network, Table 3 | F1 0.939 |
| DF, six-month concept drift, Table 5 | F1 0.685 |
| DF under Conflux, guard sees one leg | F1 0.939 -> 0.379 |
| DF under Conflux, guard with 128ms latency advantage | TPR 0.189 -> 0.736 |

**First task in either track: confirm these against the actual PDF.** The table
and figure numbers came from the brief, and a transcription error in the premise
would waste the whole weekend.

## Ground rules

Both briefs are explicit about these, and they apply to anything committed here:

- No invented numbers. A failed run or missing data gets written down as a
  failed run or missing data.
- Track A: do not retune hyperparameters. The point is comparing published
  configurations, so every deviation from Appendix A Table 7 goes in
  `track-a-robustness/logs/deltas.md`.
- Track A: minimum three seeds per cell, variance reported. Single-run numbers
  are the thing being complained about.
- Track B: no Tor patches. Scoping only, and a no-go is a perfectly good
  outcome.
- Assume no network access to DUA-gated data unless stated otherwise.

## Environment note

Track A's brief assumes a single RTX 5090 on Linux. This repo lives on the
Windows box; the 5090 is the same card, so the run itself needs WSL2 or the
Linux install. Whichever gets used, record it in `deltas.md`, along with CUDA
and torch versions (Blackwell sm_120 needs cu128 or newer wheels).

## Open items before starting

1. Confirm the paper's table numbers above against the PDF.
2. ~~Inventory OSF.~~ Done, see `track-a-robustness/logs/osf-inventory.md`.
   Result: ~10.6 GB of monitored traces are open and span AU/CA/UK across month
   0/2/6, but the open-world background set is DUA-gated for one year post
   release and is not even listed. Both axes are runnable closed-world only.
3. Decide: run both axes closed-world now, or request the DUA and wait. The
   two-axis question survives closed-world; numeric comparability to their
   Table 3 and Table 5 does not.
4. Email the authors about the analysis code. The thesis says it was released;
   nothing is on OSF and no repo was found. Without it, step 2 becomes a
   five-classifier reimplementation.
