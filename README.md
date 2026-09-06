# tor-wf-lab

Two scoped weekend investigations against Shadbeh, Khajavi & Wang, *Reality
Check for Tor Website Fingerprinting in the Open World* (arXiv:2603.07412,
March 2026).

They are independent. Track A aims at an experimental result, Track B aims at a
go/no-go decision. Both are now done.

| Track | Question | Deliverable | Status |
|---|---|---|---|
| A | Are network-mismatch robustness and temporal-drift robustness genuinely distinct axes, with no classifier good at both? | Scatter plot + numbers table + verdict paragraph | Done. All five classifiers, both axes, 3 seeds, closed world, on the 5090. Verdict: no classifier is good at both, but the independence claim rests on RF. `docs/track-a-robustness-axes.md` |
| B | Is "Conflux scheduling that mitigates LowRTT latency bias" a viable multi-week project? | Memo with go/no-go | Done, and the kill test passed. Verdict: go, narrowed. `docs/track-b-memo.md` |

## Layout

```
prompts/                    the two briefs, verbatim, treated as read-only
track-a-robustness/
  src/                      fetch and verify, loaders, the five classifiers, runners, plot
  data/                     OSF traces, gitignored, 9.9 GB
  results/                  per-classifier JSON, generated tables, the scatter plot
  logs/                     deltas.md, paper-numbers.md, osf-inventory.md
  RUNBOOK-5090.md           what ran on the GPU box, and what it cost
track-b-conflux/
  notes/                    01-05 scoping, 06-07 measurement, 08-09 Shadow
  src/                      first-segment detector, the two trace measurements
  shadow/                   Shadow experiment generator, pcap analysis, sweep
  results/                  JSON and figures for both measurements and the sim
docs/                       the two finished writeups, plus correspondence/
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

**Confirmed against the PDF on 2026-09-06.** All seven match the thesis exactly,
with no transcription error in the brief. The thesis numbers the tables
differently (brief Table 3 = thesis Table 4.1, brief Table 5 = thesis Table 4.3,
brief Appendix A Table 7 = thesis Appendix C Table C.1). Full check, both tables
in full, and the hyperparameter table:
`track-a-robustness/logs/paper-numbers.md`.

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

Track A's brief assumes a single RTX 5090 on Linux. There are two machines:

- **This one**, `owen-GR9`: Ubuntu 24.04.4 native, Ryzen 9 5900HX (16 threads),
  30 GB RAM, no CUDA GPU. Integrated AMD graphics only, and gfx90c is not a
  supported ROCm target, so it is CPU-only in practice.
- **The Windows box**, which has the 5090. Any run there needs WSL2 or the Linux
  install, and Blackwell sm_120 needs cu128 or newer wheels.

Division of labour that followed from that: staging, verification and k-FP on the
laptop; DF, Tik-Tok, RF and Holmes, all CNNs (Table C.1), on the 5090. The 5090
box turned out to have no WSL, so those ran on native Windows Python with
torch 2.11.0+cu128; capability `(12, 0)` and `sm_120` were confirmed before any
training. Whichever machine a result came from is recorded in `deltas.md`, along
with CUDA and torch versions.

Local setup on this machine: `.venv` (Python 3.12.3, numpy / scipy / sklearn /
matplotlib, no torch). Data lives in `track-a-robustness/data/`, gitignored.

## Open items

1. ~~Confirm the paper's table numbers against the PDF.~~ Done, all seven exact,
   see `track-a-robustness/logs/paper-numbers.md`.
2. ~~Inventory OSF.~~ Done, see `track-a-robustness/logs/osf-inventory.md`.
   Result: ~10.6 GB of monitored traces are open and span AU/CA/UK across month
   0/2/6, but the open-world background set is DUA-gated for one year post
   release and is not even listed. Both axes are runnable closed-world only.
3. ~~Stage the data.~~ Done. All 29 open `.npz` downloaded, 9.9 GB, all 29
   verified against the authors' sha512 lists (`src/verify_osf.py`).
4. ~~Decide: closed-world now, or request the DUA and wait.~~ Resolved by running
   it. Closed-world was the right call: the **rank ordering on both axes is
   reproduced exactly** (Spearman 1.000 against the published tables), so the
   two-axis question is answerable, even though cell values are not comparable
   and step 3 stays unsatisfiable. See `results/vs-paper.md`.
5. **Still open, but less costly than it looked.** The thesis authors' own code is
   still missing, and the email asking for it is written and unsent
   (`docs/correspondence/03-combined-request.md`). But the *original* classifier
   authors did release theirs, so RF and Holmes are transcriptions of
   `robust-fingerprinting/RF` and WFlib rather than guesses. Only DF, Tik-Tok
   and k-FP are reimplemented from paper text.
6. ~~The four CNNs need the 5090 machine.~~ Done, and Holmes ran too, making five
   classifiers rather than four. See `docs/track-a-robustness-axes.md`.
7. **Still open.** The DUA-gated background set, same email. There is **no
   platform route**: the OSF node reports `access_requests_enabled: true` but is
   public with zero child components, so OSF renders no "Request Access" control
   and the restricted data is absent rather than gated. Email is the only path.
   This is why the two earlier drafts merged into one.

## What has actually run

- **Track A, all five classifiers**, closed world, both axes, 3 seeds:
  `docs/track-a-robustness-axes.md`, numbers in
  `track-a-robustness/results/axes-table.md`, figure `results/axes.png`.
  No classifier is good at both axes. DF is best across networks (0.968) and
  loses 0.331 to six-month drift; RF is best on drift (0.748) and loses 0.250
  across networks. RF is the only classifier that inverts, fourth of five on
  network mismatch and first on drift, so the "distinct axes" claim rests on it.
  The authors' own slot-size remedy does not reproduce closed-world and makes RF
  worse on both axes (`results/rf-slot-sweep.md`). No cell value here is
  comparable to a number in the paper, but the rank ordering on both axes is
  identical to theirs.
- **Track B, first-segment sweep**: `track-b-conflux/notes/06-fs-kill-test.md`.
  A guard's first-segment ownership goes 0.448 -> 0.891 -> 0.977 as its latency
  advantage goes 0 -> 128 -> 512 ms. Detector validated at 1.0000 on non-Conflux
  controls, and the paper's 65% truncation claim reproduces at 0.659.
- **Track B, what ownership is worth**:
  `track-b-conflux/notes/07-fs-value-measured.md`. k-FP classifies 0.744 of
  first-segment traces correctly against 0.374 of the rest. Advantage buys
  ownership (x1.97 at 128 ms) far more than it buys accuracy on owned traces
  (x1.19).
- **Track B, Shadow validation**:
  `track-b-conflux/notes/09-shadow-validation.md`. Unpatched tor 0.4.9.11 in
  Shadow 3.3.0 reproduces the bias from the other direction: two identical
  guards split a download 0.512, a guard with a 64 ms advantage takes 0.71.
  Byte share plateaus near 0.78 because LowRTT falls back to the slow leg once
  the fast leg's cwnd fills. Harness in `track-b-conflux/shadow/`.
