# Q5. Has anyone already done this?

Searched 2026-09-06: Tor's GitLab issue tracker via its API, the tor-dev
archives, proposal 329 itself, the tor source tree, and the WF literature.
Nothing found that does the specific thing. Details and the one real
competition risk below.

## Tor's own tracker: nothing

Queried the open issues of `tpo/core/tor` for "conflux", "scheduler" and
"fingerprinting" (GitLab API, no auth). The conflux issues that exist are bugs
and feature work: exit-node consistency (#41291), assertion failures (#41037,
#41049, #40830), prebuilding behaviour (#40862, #40893, #40981), onion-service
support (#40716), metrics (#40784), removing validation checks (#40823). The
scheduler hits are all KIST-era cell scheduler issues, a different subsystem.
Nothing proposes changing conflux scheduling policy, and nothing mentions
website fingerprinting in a conflux context.

So on the Tor side this is **unclaimed but known-unfinished**, which is a good
position to enter: the tree is full of `TODO-329-TUNING`, BLEST_TOR is specified
in proposal 329 section 3.4 and never implemented, and CWNDRTT is implemented
and unreachable.

## Proposal 329 itself

Section 3 specifies four schedulers and is explicit that "the scheduling
algorithms are currently in flux, and will be subject to change". It already
contemplates the design axis this project would work on, including
direction-asymmetric policies. It does not discuss fingerprinting or latency
bias as an adversarial property.

## Literature: adjacent, not the same

| Work | What it is | Why it is not this |
|---|---|---|
| TrafficSliver, De la Cadena et al., CCS 2020 | Client-side splitting across multiple entry nodes as a WF defense, drops attack accuracy below about 14% | Splitting across *different guards* to deny any one of them the full trace. Predates Conflux, is not Conflux's scheduler, and assumes the client controls the split. |
| Splitting Hairs and Network Traces, Beckerle, Magnusson, Pulls, WPES 2022 | Improved attacks against traffic-splitting defenses | Attack side. Useful as the adversary model to evaluate against, not competition. |
| MUFFLER, 2025 (arXiv 2504.07543) | Dynamic connection shuffling and splitting for Tor obfuscation | A new defense mechanism, not a change to Conflux scheduling. |
| WF survey, arXiv 2510.11804, Oct 2025 | Survey of WF attacks and defenses | Abstract covers padding, regularization, morphing, adversarial perturbation. Multipath scheduling is not among the defense families it names. |

The pattern across the literature is splitting-as-a-defense designed from
scratch, or attacks on it. Nobody appears to have treated the *already deployed*
Conflux scheduler as the object to modify.

## The one real risk: the authors themselves

The Reality Check paper's conclusion says it outright (thesis section 6, p.46):

> "Future work can address this vulnerability by designing Conflux scheduling
> algorithms that mitigate latency bias."

That is the brief's project, named as future work by the group that has the
guard relay, the crawler, the ground-truth client instrumentation and the
open-world dataset that nobody else can get for a year. If they are working on
it, they will finish first and they will have a better evaluation.

This is not a technical no-go, but it changes what the project should aim at.
Competing on "who builds the better scheduler and shows the bigger recall drop"
is a losing race. Two positions are defensible:

1. **Get to Tor first, not to a venue first.** Make CWNDRTT reachable, add the
   bias floor as a consensus parameter, measure the performance cost honestly,
   and take it to tor-dev. That is engineering the authors are unlikely to do,
   and it is the path by which any of this reaches users.
2. **Ask them.** Draft 01 in `docs/correspondence/` is already going to Tao Wang
   about the analysis code. One sentence asking whether anyone is working on the
   scheduling follow-up costs nothing and resolves this risk in days, which is
   much better than discovering it in week three.
