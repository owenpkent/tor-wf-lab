# Track B: Conflux scheduling as a WF defense. Go or no-go?

Scoping only, 2026-09-06. No Tor patches were written. Sources: `tor.git` at
commit 3937194 (2026-09-03), proposal 329, the SFU thesis version of
arXiv:2603.07412, Tor's GitLab issue API, and the WF literature. Working notes,
one file per question, in `track-b-conflux/notes/`.

## Verdict: go. The premise is measured, not assumed, and the project got smaller

Not the project as framed. "Design a Conflux scheduling algorithm that mitigates
latency bias" is the paper's own stated future work, which makes it a race
against the group holding the guard relay and the gated dataset. What is worth
multiple weeks is narrower, lands where the authors will not go, and is now
aimed by measurement rather than by guesswork:

> De-bias **which leg carries the start of the load**, ship it as a consensus
> parameter alongside Tor's already-written but unreachable low-reorder
> scheduler, and take the measured time-to-first-byte cost to tor-dev.

Three things moved between the scoping questions and this verdict, all of them
from open data on a laptop in an afternoon.

**The mechanism is confirmed.** First-segment ownership tracks latency advantage
directly: 0.448 with no advantage, 0.891 at 128 ms, 0.977 at 512 ms. The
detector returns exactly 1.0000 on non-Conflux control traces, and the paper's
own "about 65% of traces hold less than half a load" reproduces at 0.659 without
being aimed at. This is no longer a premise the project rests on; it is a result
the project starts from.

**The attack is one term, not two.** Measuring what ownership is worth, rather
than inferring it, gives 128 ms of advantage a x1.97 multiplier on *how often*
the guard owns the first segment and only x1.19 on its accuracy on the traces it
owns. That kills an earlier read of these numbers, made from the paper's TPR
under the assumption that non-first-segment traces contribute nothing. They
contribute plenty: 0.374 accuracy, forty times chance.

**So the intervention is the smallest one available.** If ownership is the
attack, the thing to change is the initial leg choice, which lives in one
function, `conflux_pick_first_leg()` (`conflux.c:600`), plus the exit's
equivalent. That is a smaller and far more reviewable change than a stateful
first-K scheduler, and it targets the dominant term. Candidate A, which the
inferred decomposition had demoted, is back as a shippable measure on its own.

**What that buys, and where it stops.** Randomizing ownership removes the
*advantage*, taking the attacker from 0.891 back toward 0.448 ownership. It does
not touch the 0.744 accuracy the guard gets on traces it owns even with no
advantage at all, which is Conflux's residual leak and is not a latency-bias
problem. Anything below that ceiling needs candidate B's thinning of the prefix.
Two deliverables, then: **A is the engineering win, B is the research
contribution.**

### Conditions on the go

1. **Send the authors question first.** It is already in
   `docs/correspondence/01`, unsent. Their conclusion names this project as
   their future work, and they have the guard, the crawler and the gated
   dataset. One sentence resolves in days what would otherwise surface in
   week three.
2. **Do not quote closed-world numbers as if they were the paper's.** Everything
   above is closed-world accuracy over monitored classes. The paper's TPRs are
   open world at a fixed 0.5% FPR, where seeing more of a load mainly buys
   precision, which a closed-world metric cannot see. The x1.19 enrichment term
   is a lower bound on what the open world would show.
3. **Kill conditions that still apply.** If the authors are already building it,
   stop. If a Shadow run shows the TTFB cost of randomizing the first leg is
   worse than roughly d/2 on benign leg pairs, stop, because the performance
   argument is then unwinnable at tor-dev.

## 1. How LowRTT picks the primary leg

`conflux_decide_next_circ()` (`conflux.c:672`) picks the first leg by lowest
non-zero RTT (`conflux.c:600`), then dispatches to one of three RTT-ordered
schedulers: MinRTT (`conflux.c:275`), LowRTT (`conflux.c:307`), CWNDRTT
(`conflux.c:431`). LowRTT takes the lowest-RTT leg that still has congestion
window room. Both switch limiters that were meant to rate-limit leg changes are
inert in the current tree: `cells_until_switch` is always 0 and `cfx_drain_pct`
defaults to 0.

The decision reads exactly two pieces of state, `leg->circ_rtts_usec` and the
leg's cwnd. No history, no byte counters, no randomness, which is why the bias
holds steady across a page load instead of averaging out.

Two things the proposal does not make obvious, both of which matter:

- **The client chooses the exit's download scheduler.** The client's requested
  UX rides in the LINK cell and the exit does
  `conflux_choose_algorithm(leg->link->desired_ux)` (`conflux_pool.c:513`).
  Default `throughput` maps to LowRTT. It is already a torrc option,
  `ConfluxClientUX`. The guard-observable direction is therefore configurable
  from the client today.
- **CWNDRTT is dead code.** It is implemented, dispatched, and unreachable,
  because no UX value maps to it. The switch statement carries
  `TODO-329-TUNING: Pick better algs here`. BLEST_TOR, specified in proposal 329
  section 3.4, was never implemented at all.

## 2. The crux, and it does not kill the project

The brief's kill condition was: if spreading traffic more evenly necessarily
reintroduces head-of-line blocking, stop. It does not, for two reasons, and
there is a third that constrains the design.

**The premise is already refuted inside Tor's tree.** CWNDRTT uses an auxiliary
leg only up to `cwnd_leg * min_rtt / leg_rtt`, the amount that arrives at about
the same time as the fast leg's data, and its docstring claims reorder bloat
confined to slow start. Head-of-line blocking is a function of reorder distance,
not of using both legs.

**The defense only needs the first segment.** The paper's attack is built on who
owns the beginning of the load: the prefix is feature-rich, primary-leg switches
often come only after about 50 KB, and roughly 65% of monitored traces hold less
than half the load's cells. A policy can de-bias the first segment and hand over
to LowRTT, which bounds the cost to the phase where Conflux's throughput benefit
has not appeared yet.

**But the cost is highest exactly where the bias matters.** De-biasing means
sometimes starting on the slower leg, and when the asymmetry is the paper's
128 ms, that is roughly a 64 ms average time-to-first-byte regression on
affected loads. Nothing escapes that. What softens it: benign leg pairs differ
by about 10 ms rather than 150, so most users pay almost nothing, and a large
advantage is usually manufactured by the attacker, so removing the payoff
removes an incentive rather than merely moving a constant.

The honest restatement of the crux is therefore not "is it possible" but "how
much TTFB is Tor willing to spend to make first-segment ownership
unpredictable, and does spending it actually cost the attacker recall".

## 3. Candidate policies

Full sketches in `notes/03-candidate-policies.md`.

**A. Randomized first leg.** Pick the initial leg at random among legs with a
valid RTT, independently at each endpoint, then resume LowRTT. Attacks the
paper's first-segment definition directly, since a first segment requires
winning at both endpoints. *Tradeoff:* about d/2 of added TTFB, and the
advantaged guard still carries more of the tail because LowRTT resumes.

**B. CWNDRTT for the first K cells, LowRTT after.** Make the existing algorithm
reachable and use it for the first segment only. The only candidate that
degrades the features rather than reassigning ownership, since the guard sees a
thinned, interleaved prefix. *Tradeoff:* out-of-order queue memory during slow
start, capped by the existing `cfx_max_oooq_bytes`, and the weakest guarantee,
because CWNDRTT still prefers the min-RTT leg whenever it can send.

**C. RTT quantization with a bias floor.** Treat legs within T milliseconds as
equivalent and break the tie randomly, T shipped as a consensus parameter beside
the existing `cfx_*` family. Best fit to the data, whose TPR curve is flat until
the advantage nears the 150 ms path delta and then rises sharply. *Tradeoff:* T
is an arms-race constant, and it touches all three schedulers.

Build order: B, then A, then propose C to tor-dev.

## 4. Shadow

Usable, and the right tool for the latency delta, but third-cheapest of four
environments and not where to start. Tor's own WF-defense guidance
(`doc/HACKING/CircuitPaddingDevelopment.md` section 4) ranks trace simulation
first for iteration, rules out Chutney for anything latency-dependent, puts
Shadow third, and calls live-network-with-your-own-relays the gold standard.

A minimal experiment needs one client, two guards with a controllable RTT delta,
one shared exit, congestion control and Conflux on, and enough volume to cross
slow start. It does **not** need a browser: the measurement at this stage is the
first-segment rate and the share of the first N cells, which are scheduler
properties. `tgen` is enough, and the WF classification belongs in a separate
offline step.

Setup cost: two to four days for Shadow plus tornettools from scratch, and a 1%
network runs to about 30 GiB of RAM for an hour of simulated time. A hand-built
topology of six or seven nodes is hours to a day and contains the whole effect,
since the effect is local to one conflux set. Scale only matters once the claim
becomes "and it does not hurt the network".

## 5. Prior art

Nothing does this. Tor's open issues contain no conflux scheduling-policy work
and no conflux-plus-fingerprinting issue; the conflux issues are bugs, onion
service support and metrics. Proposal 329 contemplates the design axis and says
the schedulers are "in flux", without treating latency bias as adversarial. The
literature is adjacent: TrafficSliver (CCS 2020) splits across entry nodes
rather than modifying Conflux, Splitting Hairs (WPES 2022) attacks splitting
defenses, MUFFLER (2025) is a separate obfuscation mechanism, and the October
2025 survey does not list multipath scheduling among defense families.

**The real risk is the authors.** Their conclusion names this project verbatim
as future work, and they hold the guard, the crawler, the ground truth
instrumentation and a dataset nobody else can get for a year. Competing on
evaluation quality is a losing race; getting the change into Tor is not. Add one
sentence to the draft email already sitting in `docs/correspondence/` asking
whether anyone is working on the scheduling follow-up. It costs nothing and
resolves the risk in days.

## 6. The kill test: run, and passed

The project rests on one mechanism, latency advantage buying first-segment
ownership. It is now measured, from open data, on this laptop. Full write-up in
`track-b-conflux/notes/06-fs-kill-test.md`, figure at
`track-b-conflux/results/fs-rate.png`.

| Guard advantage | FS rate | Median cells the guard sees |
|---|---|---|
| 0 ms | 0.448 | 1,436 |
| 32 ms | 0.568 | 1,717 |
| 64 ms | 0.675 | 1,808 |
| 128 ms | 0.891 | 2,081 |
| 256 ms | 0.961 | 2,486 |
| 512 ms | 0.977 | 2,947 |

Monotone, with the knee between 64 and 128 ms, where the paper's TPR curve also
turns. Two checks say the detector is right rather than lucky: on non-Conflux
traces, where each load has exactly one leg and every trace must be a first
segment, it returns 1.0000 on 22,496 traces; and the paper's claim that about
65% of Conflux traces hold less than half a page load reproduces at 0.659
without being aimed at. The unmanipulated AU and UK clients sit at 0.211 and
0.151, which is the same bias occurring naturally when the guard is simply the
slower leg.

**What ownership is worth, measured rather than inferred.** A second run trains
k-FP per condition and scores the held-out traces separately by whether the
guard owned the first segment (`notes/07-fs-value-measured.md`,
`results/fs-kfp.png`):

| Advantage | Accuracy given FS | Accuracy given non-FS | Ratio |
|---|---|---|---|
| 0 ms | 0.744 | 0.374 | 2.0 |
| 128 ms | 0.886 | 0.328 | 2.7 |
| 512 ms | 0.907 | 0.236 | 3.8 |

Decomposed against the no-advantage baseline, 128 ms of advantage multiplies how
often the guard owns the first segment by **1.97** and its accuracy on the
traces it owns by **1.19**. **Ownership is the attack; enrichment is second
order.**

This also corrects a decomposition made earlier the same day. Inferring the
conditional from the paper's TPR, under their implicit assumption that
non-first-segment traces contribute nothing, suggested it doubled. Measured, it
rises by a fifth, and the assumption is simply false in a closed world: k-FP
classifies 0.374 of non-first-segment traces correctly with no advantage at all,
forty times chance. Two caveats keep this from being over-read: closed-world
accuracy cannot see precision, which is most of what seeing more of a load buys
at a fixed 0.5% FPR, and the non-FS subset thins to 87 traces by 512 ms.

**Consequence for the design.** Candidate A, randomizing the initial leg, is
back in contention on its own, because it attacks the dominant term. Candidate B
remains the better design, but for a different reason than first supposed: it
degrades the features on the traces the guard does own, which is the 0.744
baseline randomization leaves untouched.

**What candidate A would buy, projected.** The measured conditionals price the
policy without running it. Hold the two accuracies fixed and vary only how often
the guard owns the first segment, which is what randomizing the initial leg
changes:

| Advantage | Measured ownership | Measured accuracy | Projected at ownership 0.448 | Projected at 0.25 |
|---|---|---|---|---|
| 0 ms | 0.448 | 0.5399 | 0.5399 | 0.4665 |
| 32 ms | 0.561 | 0.6225 | 0.5786 | 0.5019 |
| 64 ms | 0.674 | 0.6860 | 0.5861 | 0.4986 |
| 128 ms | 0.884 | 0.8217 | 0.5783 | 0.4678 |
| 256 ms | 0.961 | 0.8786 | 0.5481 | 0.4204 |
| 512 ms | 0.977 | 0.8911 | 0.5366 | 0.4037 |

**The projected curve is flat.** That is the property a defense wants: buying
latency stops paying. Today an attacker turns 0.540 into 0.891 by manufacturing
half a second of advantage. With ownership pinned at the no-advantage rate, the
same half second is worth 0.537, slightly *less* than doing nothing, and the
best it can do anywhere on the sweep is about +0.05 at 32 to 64 ms, where
accuracy on owned traces has risen but ownership no longer follows.

The 0.25 column is the more likely landing point, and it is worth understanding
why it is below the 0.448 baseline rather than equal to it. A first segment
requires being primary at *both* endpoints. Independent coin flips at each end
give 0.25. The observed no-advantage rate is 0.448 rather than 0.25 precisely
because the two endpoints are not independent today: both order the same two
paths by RTT, so they usually agree. Randomization breaks that correlation, and
the broken correlation is a second win on top of removing the bias.

Three caveats, since this is arithmetic on measured conditionals and not an
experiment:

- It assumes the conditionals hold under the new policy. For candidate A that is
  reasonable on the FS side, because randomizing only the *initial* leg leaves
  LowRTT to resume afterwards, so an advantaged leg that wins the start still
  carries more of the tail. It is optimistic on the non-FS side for the same
  reason: a guard that loses the start still has its advantage and would carry
  more of the tail than the traces measured here.
- Closed world again, so these are accuracies over monitored classes, not TPRs
  at a fixed FPR.
- It says nothing about the time-to-first-byte cost, which is the other half of
  the argument and needs Shadow.

## Summary

| Question | Answer |
|---|---|
| 1. LowRTT mechanics | Lowest-RTT leg with cwnd room; client picks the exit's algorithm; CWNDRTT is unreachable dead code |
| 2. Crux | Survives. Reorder can be bounded, and only the first segment needs de-biasing, but TTFB cost is highest where the bias matters most |
| 3. Policies | Randomized first leg (now the primary, it attacks the dominant term); CWNDRTT-for-first-K (goes below the residual leak); RTT quantization with a consensus-parameter floor |
| 4. Shadow | Yes, small hand-built topology, hours to a day; full tornettools is the wrong first target |
| 5. Prior art | Unclaimed in Tor and in the literature. Risk is the paper's own authors |
| 6. Kill test | **Passed.** FS rate 0.448 -> 0.891 -> 0.977 across the advantage sweep, detector validated at 1.0000 on single-leg controls. Follow-up measurement: ownership x1.97 at 128 ms, enrichment only x1.19 |
| 6a. Projection | Pinning ownership at the no-advantage rate flattens the curve: a 512 ms advantage would be worth 0.537 instead of 0.891, and at most about +0.05 anywhere on the sweep |
| **Verdict** | **Go.** The mechanism is measured, the attack is one term rather than two, and the intervention that matters is one function. Ship candidate A as the engineering win and candidate B as the research contribution. Conditional only on asking the authors what they are already doing |
