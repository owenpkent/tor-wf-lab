# Track A step 1: OSF inventory

Date: 2026-09-06. Source: OSF public API on `osf.io/9m8ea` (no auth), plus the
SFU thesis PDF as a secondary source for dataset description. Marked below where
something is verified against the listing versus taken from the paper text.

## What is openly downloadable

**Verified.** Two folders under osfstorage, roughly 10.6 GB across ~31 `.npz`
files. A direct download of `pre-month0-cfx0-ca.npz` returned HTTP 200 with no
login and no agreement.

| Folder | Files | Size | Naming |
|---|---|---|---|
| `pre-conflux/` | 5 | ~1.4 GB | `pre-month0-cfx0-{ca,au}.npz`, `-nga` variants, sha512sums |
| `post-conflux/` | 26 | ~9.2 GB | `post-month{0,2,6}-cfx{0,2}-{ca,au,uk}.npz`, plus `-nga` and `-rtt-{032,064,128,256,512}` variants, sha512sums |

So the open portion is factorial across three client sites (CA, AU, UK), three
timepoints (month 0, 2, 6), Conflux on/off, a no-guard-advantage condition, and
five latency-advantage settings.

`pre-conflux/` has no UK file, although thesis Table 3.2 lists a pre-Conflux UK
client with 61,641 monitored traces. **Unconfirmed** why.

## What is gated

**Verified**, and stated identically in the OSF wiki and thesis Appendix B
(p.54): the synthetic closed-world monitored data is public under CC BY-NC 4.0.
The open-world background traffic, being real traffic from real Tor users,
requires academic research approval and stays restricted for one year after
release. The OSF node has access requests enabled.

The restricted files are not merely locked, they are **absent from the public
listing entirely**. Nothing to see the shape of.

No DUA contact, form, or lead time is stated in either the wiki or the thesis.
Only OSF's generic access-request mechanism was found. **Unconfirmed.**

## Consequence for the two axes

This is the answer the brief's step 1 asks for, and it is a qualified no.

The open files span AU/CA and a six-month spread, so both axes are constructible
**for the monitored class only**. But the paper's cross-network table (train AU,
test CA) and its concept-drift table are open-world results: every F1 in them is
computed against the real non-monitored background. Those specific numbers
cannot be reproduced without the DUA.

Closest feasible substitute, per the brief's instruction to propose one rather
than proceed quietly: **run both axes closed-world.** Same five classifiers,
same published hyperparameters, same train-AU/test-CA and month0-to-month6
splits, scored closed-world. The two-axis *question* survives, because whether
RF and DF trade places across the two axes is a claim about the classifiers, not
about the base rate. What does not survive is numeric comparability to their
Table 3 and Table 5. Closed-world F1 will be higher across the board and must
never be placed alongside their numbers as if it were the same measurement.

## Second blocker: no code

**Unconfirmed but likely.** The thesis intro says both dataset and analysis code
are released. No code exists in the OSF file listing, and a web search found no
GitHub repository. Reference [27] in the bibliography is a self-citation to the
OSF project, not to code.

If that holds, step 2 changes from "get their code running" to "reimplement five
classifiers from their original papers at the hyperparameters in Appendix A
Table 7." k-FP, DF and Tik-Tok have well-known public reference implementations.
Holmes is the recent one and the least certain. This is a large delta and it
undermines the brief's premise of comparing published configurations rather than
reimplementations.

**Correction, 2026-09-06.** An earlier version of this line said "RF is
sklearn". That is wrong. RF here is Robust Fingerprinting, and thesis Table C.1
gives it as a 2D CNN over a Traffic Aggregation Matrix of length 1800. Only k-FP
is a random forest. Four of the five classifiers therefore need a GPU, not
three. See `paper-numbers.md`.

Worth one direct email to the authors before reimplementing anything.

## Incidental finding for Track B

The `-rtt-{032,064,128,256,512}` and `-nga` variants mean the guard
latency-advantage experiment behind Track B's premise, the one where TPR
recovers from 0.189 to 0.736 at 128 ms, sits in the open portion. The empirical
half of Track B's background can be checked without a DUA.

## Table numbering caution

The thesis numbers these as Table 3.2, 4.1, 4.3 and Appendix C Table C.1. The
brief cites Table 3, Table 5 and Appendix A Table 7. Same content, different
version numbering. Confirm against whichever document is being cited before
quoting any figure.


## Addendum, 2026-09-06: which files each axis actually needs

Settled after reading the thesis rather than the brief, see `paper-numbers.md`.

- Cross-network is the **pre-Conflux** dataset: `pre-month0-cfx0-au.npz` train,
  `pre-month0-cfx0-ca.npz` test.
- Drift is the **UK** client: `post-month{0,2,6}-cfx0-uk.npz`. Not AU or CA, and
  UK is in any case the only site with a month-2 cfx0 file.

All 29 open `.npz` files were downloaded on 2026-09-06 and all 29 verify against
the authors' sha512 lists. The `9m8ea-osfstorage-archive.zip` that OSF serves as
a bulk download holds the same 31 entries at the same sizes and contains no code,
which is a second confirmation of the no-code finding above.

Site attrition, not mentioned in the paper and relevant to the drift axis: the
nominal label space is 112 sites, but six of them (16, 40, 60, 76, 95, 100) are
absent from the UK month-6 collection and site 100 is already absent from AU
month 0. Part of any six-month recall drop is sites that stopped existing.
