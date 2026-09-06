# Does stock tor in Shadow reproduce the latency bias?

Run 2026-09-06 on `owen-GR9`. Harness in `../shadow/`, numbers in
`../results/shadow-sweep.json`, figure `../results/shadow-sweep.png`.

Yes. With no advantage the two guards split the client's download 0.51 / 0.49,
and the bias appears as soon as one guard is closer.

## Setup

Shadow 3.3.0, **unpatched tor 0.4.9.11** from the Ubuntu package, tgen 1.1.2.
Built on Shadow's own private Tor network example (one directory authority with
pre-generated keys, four relays, two exits, a tor client, tgen at both ends),
adapted in four places by `shadow/gen_exp.py`:

1. Three network nodes instead of one, so the two guards sit at different
   latencies from the client. One-way edge latency differs by advantage/2, since
   the advantage is stated as an RTT difference.
2. Client pins `EntryNodes` to relay1 and relay2 with `NumEntryGuards 2` and
   `StrictNodes 1`. Conflux excludes a leg's guard when building the next one
   (`conflux_pool.c:1223`), so the two legs land on the two pinned guards.
3. `MaxCircuitDirtiness 20` so a run produces many conflux sets rather than one.
4. `cfx_enabled=1` added to the authority's existing `ConsensusParams`, though
   Conflux is on by default in 0.4.9 (`CONFLUX_ENABLED_DEFAULT` is 1).

Conflux really is in use, not assumed: the client's info log shows 12 sets
launched and 24 `conflux_process_linked()` calls per run.

Measurement: per-guard pcap, filtered to packets to and from the client, giving
the advantaged guard's share of client downstream bytes. 10 seeds per point.

## Result

| Guard advantage | Share of client downstream | sd | min | max |
|---|---|---|---|---|
| 0 ms | **0.5120** | 0.058 | 0.390 | 0.579 |
| 32 ms | 0.6279 | 0.099 | 0.473 | 0.742 |
| 64 ms | 0.7093 | 0.084 | 0.513 | 0.799 |
| 128 ms | 0.7110 | 0.081 | 0.557 | 0.810 |
| 256 ms | 0.7240 | 0.140 | 0.414 | 0.896 |
| 512 ms | 0.7803 | 0.133 | 0.531 | 0.901 |

The 0 ms row is the check that matters: with identical guards the split is a
coin flip, so the harness is measuring the bias and not some artefact of the
topology or of which relay is named first.

## Two things the simulation says that the traces could not

**The plateau is real, and it is LowRTT's congestion window.** Byte share
saturates around 0.72 to 0.78 and does not approach 1.0 even at an absurd
512 ms. That follows directly from the algorithm: LowRTT takes the lowest-RTT
leg *that still has cwnd room* (`conflux.c:307`), so once the fast leg's window
fills, the overflow goes down the slow leg regardless of how slow it is. An
advantaged guard cannot capture the whole download by being fast; it can only
capture the part that fits in its window.

**Ownership and share are different quantities and behave differently.** The
real traces gave first-segment *ownership* saturating at 0.977
(`06-fs-kill-test.md`). Shadow gives byte *share* saturating near 0.78. Both are
consistent with the same mechanism, and neither number should be quoted against
the other. Owning the start of a load is close to all-or-nothing; carrying its
bytes is not.

## Limits, so this is not over-read

- **Byte share is a proxy.** Per-set first-segment attribution from the pcaps is
  the measurement that would compare directly with note 06, and it is not done.
- **Bulk transfers, not page loads.** tgen streams are not browser traffic, and
  the WF-relevant prefix structure is therefore only approximated.
- **12 conflux sets per run**, so per-run variance is large. The sd column is
  mostly that, not measurement error.
- **The knee is earlier than in the real data**, 32 to 64 ms here against 64 to
  128 ms in the traces, because this simulated circuit's base RTT is not the
  real network's. The shape transfers; the x-axis calibration does not.

## What this unlocks, and what it cost

The harness now prices a scheduler change: run the same sweep against a patched
tor, and the difference is the defense's effect, while tgen's own stream timings
give the time-to-first-byte cost the memo says is the other half of the
argument. Both fall out of one run.

Cost was under an hour of wall clock in total. Shadow builds in about five
minutes, a 30-simulated-minute run takes roughly 7 seconds, and the full 60-run
sweep finished in under ten. The memo's estimate of two to four days for
Shadow plus tornettools was for the full network model, which is still out of
reach here on memory; the small topology it recommended instead turned out to
be far cheaper than that.
