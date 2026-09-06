# Q3. Candidate policies

Three, in increasing order of how much of Tor they touch. All are sketches; no
patch was written this session, per the brief's hard constraint.

## A. Randomized first leg

Replace the lowest-RTT rule in `conflux_pick_first_leg()` (`conflux.c:600`) with
a random choice among legs that have a valid RTT, and make the exit do the same
for its initial send. Everything after the first segment stays LowRTT.

The change is small, maybe twenty lines plus a consensus parameter to control
the mix, and it directly attacks the paper's first-segment definition: a leg is
a first segment only if it is primary at *both* endpoints, so randomizing the
two choices independently makes joint ownership a coin flip rather than a
property of RTT.

**Tradeoff:** pure time-to-first-byte. With two legs and a delta of d, expected
TTFB rises by about d/2. At the paper's 128 ms that is a 64 ms average
regression on page-load start, which is a real user-visible cost and the kind of
thing Tor's performance people will push back on. It also does nothing about the
rest of the load: an advantaged guard still ends up carrying more total bytes,
because LowRTT resumes immediately.

## B. CWNDRTT for the first segment, LowRTT after

Make `CONFLUX_ALG_CWNDRTT` reachable (one case in `conflux_choose_algorithm()`,
`conflux_pool.c:150`, plus a `ConfluxClientUX` value), and use it for the first
K cells of a set's data transfer before falling back to LowRTT. K on the order
of the first segment the paper describes, so roughly 1,000 cells or the end of
slow start.

This is the only candidate that degrades the *features* rather than
reassigning ownership. CWNDRTT interleaves the auxiliary leg up to the RTT-ratio
bound, so the advantaged guard sees a thinned, gappy version of the feature-rich
prefix instead of a clean one. The reordering cost is bounded by construction
and, per the function's own docstring, confined to slow start.

**Tradeoff:** out-of-order queue memory at the client during the first segment,
which is precisely the cost `cfx_max_oooq_bytes` exists to cap, plus a modest
throughput loss while the auxiliary leg is rate-limited. Also the weakest
guarantee of the three: an attacker with a large enough advantage still gets the
min-RTT leg first, because CWNDRTT still prefers it whenever it can send.

## C. RTT quantization, or a bias floor

Treat two legs whose RTTs differ by less than a threshold T as equivalent, and
break the tie randomly, in every one of the three schedulers and in the
first-leg pick. Ship T as a consensus parameter next to the existing `cfx_*`
family (`conflux_params.c`).

This is the policy that best matches what the data actually shows. The paper's
TPR curve is flat and low until the advantage approaches the 150 ms
client-to-client delta and then rises sharply, and Appendix C.1 shows the same
threshold shape from the RF side. A floor removes the payoff for manufacturing a
*small* advantage, which is the cheap attack, while still avoiding genuinely bad
legs, which is what Conflux is for.

**Tradeoff:** T is an arms-race constant. An attacker who can manufacture 128 ms
can manufacture T + 128 ms, so this raises the cost of the attack rather than
removing it, and picking T means picking whose latency differences count as
real. It is also the most invasive of the three in terms of review surface,
since it changes all three schedulers rather than adding a fourth.

## Which one to build first

B, then A. B is nearly free to implement because the algorithm already exists
and is tested, and making dead code reachable is a contribution to Tor
regardless of whether the WF story holds up. A is the cleanest experiment for
isolating the first-segment effect. C is the one to propose to tor-dev if the
first two show the effect is real, because a consensus parameter is how Tor
actually ships this kind of change.
