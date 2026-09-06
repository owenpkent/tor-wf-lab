# Can Shadow run here, and what would the first experiment be?

Answered by doing, 2026-09-06, on `owen-GR9`.

## Shadow runs on this machine

Built Shadow 3.3.0 from source (commit 49180a3, 2026-09-03) into `~/.local`.
Ubuntu 24.04 is an officially supported platform and kernel 7.0.0 is well past
the 5.10 minimum. A minimal simulation, real `curl` fetching from a real
`python3 -m http.server` over a simulated 1 Gbit switch, completes with exit 0
and the client receives the page. So the simulator itself is not a risk here.

Build took about five minutes on 16 threads. It needed none of the extra
packages the docs list beyond what the machine already had.

One gotcha worth recording: a process still running at `stop_time` is an error
unless the host declares `expected_final_state: running`. The first run failed
with "1 managed processes in unexpected final state", which reads like a crash
and is not one.

## What is and is not in reach

| | |
|---|---|
| Hand-built topology, a client, two guards, middles, an exit, tgen | **Yes.** One to two GB of RAM, minutes to run |
| Full tornettools model at 1% of the Tor network | **No.** Wants roughly 30 GiB for an hour of simulated time; 24 GB is available here |

That matches the memo's position anyway: the effect is local to one conflux set,
so scale only becomes interesting once the claim changes to "and it does not
hurt the network".

## The tor binary is not a problem either

Ubuntu 24.04 packages **tor 0.4.9.11**, the same release series as the source
tree the mechanics in `01-lowrtt-mechanics.md` were read from, so Conflux is
present and no from-source build is needed.

## The experiment this sets up

Shadow ships a complete working private Tor network at
`examples/docs/tor/`: one directory authority with pre-generated keys, four
relays, two exits, a tor client and tgen at both ends. The adaptation needed is
small and specific:

1. **Network graph.** The example puts every host on one node with a uniform
   50 ms edge. Replace it with three nodes so the two guards sit at different
   latencies from the client. That delta is the independent variable.
2. **Client torrc.** Pin `EntryNodes` to exactly the two guards, `NumEntryGuards
   2`, and set `ConfluxClientUX`, which is the option that decides the exit's
   download-direction scheduler.
3. **Authority torrc.** The example already sets `ConsensusParams cc_alg=2`, so
   `cfx_enabled=1` goes in the same place.
4. **Measurement.** Per-host pcap at each guard, then the share of the first N
   kilobytes each guard carried. That is an approximation of first-segment
   ownership rather than the cell-level ground truth the paper had from
   instrumented clients, and it should be described that way.

The milestone is a **validation**, not a defense evaluation: run stock,
unpatched tor and check that ownership tracks the latency delta the way it does
in the real traces, 0.448 at no advantage rising towards 0.9 by 128 ms
(`06-fs-kill-test.md`). If Shadow does not reproduce that with unmodified tor,
it cannot price a scheduler change either, and that is worth knowing before
anybody writes one. It also stays inside the brief's no-patches constraint.
