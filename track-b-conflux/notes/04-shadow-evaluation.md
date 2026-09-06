# Q4. Can Shadow evaluate these?

Yes, but it should not be the first tool, and Tor's own documentation says so.

## What Tor's developers recommend for this exact situation

`doc/HACKING/CircuitPaddingDevelopment.md` section 4 is the closest existing
guidance, written for circuit-padding WF defenses. It ranks four environments:

1. **Pure trace simulation** (Pulls's `circpad-sim`), for tuning a defense over
   many iterations, because Shadow's wall clock is prohibitive at that volume.
2. **Chutney**, easy private network, but explicitly useless for anything
   latency-dependent since it runs over localhost. That rules it out here: our
   entire effect is a latency delta.
3. **Shadow**, accurate topology and latency models, more memory-efficient than
   Chutney, but "not as fast or efficient" for many iterations.
4. **Live network with your own relays**, the gold standard, made ethical by
   restricting your own clients to your own relays. This is exactly how the
   Reality Check authors collected their data.

The lesson transfers: use the cheapest environment that still contains the
effect, and Shadow is the third-cheapest of four.

## What a minimal Shadow experiment must model

- Two guards reachable by one client, with a **controllable RTT delta** between
  them. This is the independent variable and Shadow's latency model is the
  reason to use Shadow at all.
- Congestion control on (default since 0.4.7/0.4.8) and Conflux enabled, since
  the scheduler decision reads the cwnd.
- One exit shared by both legs, because a conflux set is per-exit.
- Enough transfer volume to cross slow start, so the first-segment behaviour and
  the steady-state behaviour are distinguishable.

It does **not** need a browser or real page loads. The quantity to measure at
this stage is a scheduler property, not a classification score: the fraction of
transfers where the advantaged guard is primary at both endpoints when data
starts (the paper's FS rate), and its share of the first N cells. `tgen` streams
are sufficient. Deferring the WF classification to an offline step is what keeps
this experiment small.

## Setup cost, realistically

- Shadow plus `tornettools` from scratch, for someone who has not run it: **two
  to four days** to a first trustworthy result, most of it in model generation
  and resource limits rather than in Tor itself.
- Resources: a 1% Tor network for 60 simulated minutes runs to roughly 30 GiB
  of RAM, and 10% needs hundreds of GiB. A full tornettools model is the wrong
  target anyway.
- **Cheaper target:** a hand-written Shadow topology with a client, two guards,
  two middles, one exit and a tgen server. Hours to a day, and it contains the
  entire effect, because the effect is local to one conflux set. Scale only
  matters if the claim becomes "and it does not hurt the network", which is a
  later question.

## The experiment that comes before Shadow

No simulator is needed to test the premise. The paper publishes its first-segment
detector as three rules (thesis 4.3.2): first cell after the handshake is
outgoing, at least one incoming cell within the first 10 cells, and at least one
outgoing cell within a 10-cell window after the first incoming one. The open OSF
files include `post-month2-cfx2-ca-rtt-{032,064,128,256,512}.npz` and the `-nga`
no-guard-advantage variants, all already downloaded and checksum-verified for
Track A.

So the FS-rate-versus-latency-advantage curve, which is the mechanism the whole
project rests on, can be reproduced from open data on a laptop in a day. If FS
rate does not track the advantage, no scheduler change can help and the project
ends there, at a cost of one day rather than one month.
