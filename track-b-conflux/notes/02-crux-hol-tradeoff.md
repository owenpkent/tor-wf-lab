# Q2. The crux: can latency bias go without giving up what Conflux is for?

The brief's kill condition: if every policy that spreads traffic more evenly
necessarily reintroduces head-of-line blocking, the project is dead.

## Answer: no, it is not dead, but the honest version is narrower than the
## brief's framing

Three observations do the work.

### 1. The defense only needs the first segment, not the whole load

Conflux's throughput benefit accrues over the bulk of a transfer. The WF signal
does not: the paper says the initial portion is feature-rich (thesis 4.3.2,
citing Gong and Wang), that primary-leg switches often happen only after about
50 KB, and that roughly 65% of monitored traces contain less than half the page
load's cells. Their whole attack is built on who owns the beginning.

So the policy does not have to spread evenly for the lifetime of the connection.
It has to de-bias the first segment and can then hand over to LowRTT. That
bounds the cost to roughly the slow-start phase, which is exactly the phase
where Conflux's throughput advantage has not materialized yet.

### 2. The "spread evenly implies head-of-line blocking" premise is already
### refuted inside Tor's own tree

`conflux_decide_circ_cwndrtt()` (`conflux.c:431`) uses the auxiliary leg only up
to `cwnd_leg * min_rtt / leg_rtt`, the amount whose data arrives at about the
same time as the fast leg's. Its own docstring: "out-of-order queue bloat should
be minimized to just the slow-start phase". That is a worked example of using
both legs without unbounded reordering, written by the Conflux authors, and it
is unreachable dead code today (see `01-lowrtt-mechanics.md`).

Head-of-line blocking is a function of the *reorder distance* between legs, not
of the fact that both are used. Any policy that keeps per-leg sends inside the
RTT-ratio bound keeps reordering bounded.

### 3. But the bias cannot be removed for free in the case that matters

This is the part not to gloss over. The attack condition is a large RTT
asymmetry, roughly 128-150 ms in the paper. De-biasing means sometimes sending
the first cells down the slower leg, and when the asymmetry is 128 ms, that
costs about 128 ms of time-to-first-byte on those loads. The cost of removing
the bias is largest exactly where the bias is most dangerous. No scheduling
trick escapes that; it is the same shape as every padding-versus-latency
tradeoff Tor has argued about before.

What softens it:

- In the benign case legs are similar. The paper measures roughly 10 ms between
  the UK and CA clients versus 150 ms between AU and CA, and observes that RF
  survives Conflux fine when the training and test networks have similar
  latency. Most real conflux sets are not 128 ms apart, so most users pay
  almost nothing.
- A large advantage is often manufactured. The paper's own experiment produces
  it by manipulating RTT to the client's other guards (thesis 4.3.1 and the
  `-rtt-*` datasets). A policy that stops rewarding a manufactured advantage is
  removing an attacker incentive, not just shuffling a performance constant.

### Consequence for the project

The crux question survives, but it should be restated before any design work:

> Not "can we spread traffic evenly without head-of-line blocking", which is
> already answered yes by CWNDRTT, but "how much time-to-first-byte is Tor
> willing to spend to make first-segment ownership unpredictable, and does
> spending it actually cost the attacker recall?"

The second half of that is an empirical question that the open OSF data can
answer without a simulator. That is the week-1 experiment in the memo.
