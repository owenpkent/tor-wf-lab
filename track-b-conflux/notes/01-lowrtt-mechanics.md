# Q1. How LowRTT picks the primary leg

Source: `tor.git` at commit 3937194 (2026-09-03), shallow clone, plus
proposal 329. Line numbers are that commit.

## The decision path

`conflux_decide_next_circ()`, `src/core/or/conflux.c:672`, is the entry point
every send goes through. It does three things in order:

1. If there is no current leg, `conflux_pick_first_leg()` (`conflux.c:600`)
   picks **the leg with the lowest non-zero `circ_rtts_usec`**. Legs with a
   0 RTT are skipped, because RTT is not measured until the LINKED handshake
   completes.
2. `conflux_can_switch()` (`conflux.c:382`) gates switching on
   `cells_until_switch` and on the previous leg's inflight draining below
   `cfx_drain_pct` of its cwnd. **In the current tree both switch limiters are
   inert**: `cells_until_switch` is assigned 0 in both places that set it
   (`conflux.c:645`, `conflux.c:743`), each with a `TODO-329-TUNING` comment
   suggesting it should be a cwnd, and `cfx_drain_pct` defaults to 0
   (`conflux_params.c:72`).
3. It dispatches on `cfx->params.alg` to one of three schedulers.

## The three schedulers

| Alg | Function | Rule |
|---|---|---|
| `CONFLUX_ALG_MINRTT` | `conflux.c:275` | Strictly the lowest-RTT leg. If that leg cannot send, send nothing. |
| `CONFLUX_ALG_LOWRTT` | `conflux.c:307` | Lowest-RTT leg **that still has cwnd room**. Falls to the next leg only when the fast one is blocked. |
| `CONFLUX_ALG_CWNDRTT` | `conflux.c:431` | Prefers the min-RTT leg; when it is blocked, uses an auxiliary leg only up to `cwnd_sendable() = cwnd_leg * min_rtt / leg_rtt`, i.e. only as much as arrives at roughly the same time as the fast leg's data. |

All three are RTT-ordered. There is no round-robin, no randomization, and no
byte-fairness anywhere in the file.

## Which endpoint runs which, and who chooses

This is the part that matters and it is not obvious from the proposal.

- The **client** puts `desired_ux` in the LINK cell (`conflux_cell.c:53`), taken
  from the torrc option `ConfluxClientUX` (`conflux_pool.c:1086`,
  `config.c:3579`), default `throughput`.
- The **exit** turns the client's requested UX into its own algorithm:
  `cfx->params.alg = conflux_choose_algorithm(leg->link->desired_ux)`
  (`conflux_pool.c:513`). `CONFLUX_UX_HIGH_THROUGHPUT` maps to
  `CONFLUX_ALG_LOWRTT` (`conflux_pool.c:150`).
- The **exit** replies with `DEFAULT_EXIT_UX = CONFLUX_UX_MIN_LATENCY`
  (`conflux_pool.c:137`), commented "Exits should always request min latency
  from clients", so the client schedules its uploads with MinRTT.

So the download direction, the one a guard-side WF adversary observes, is
scheduled **at the exit, under LowRTT, at the client's request**. The client
already controls that choice today through a documented torrc option
(`doc/man/tor.1.txt:373`), with values `throughput`, `latency`,
`throughput_lowmem`, `latency_lowmem`.

## Dead code worth knowing about

`conflux_choose_algorithm()` maps all five UX values onto LOWRTT or MINRTT.
**Nothing ever sets `CONFLUX_ALG_CWNDRTT`.** It is implemented, dispatched at
`conflux.c:697`, and unreachable. The switch statement carries
`/* TODO-329-TUNING: Pick better algs here*/`. Proposal 329 also specifies
BLEST_TOR, which was never implemented at all.

## State the decision depends on

Only `leg->circ_rtts_usec` (updated in `conflux_update_rtt()`, `conflux.c:707`,
from the congestion-control RTT estimate) and the leg's congestion window via
`circuit_ready_to_send()` / `cwnd_available()`. No history, no byte counters, no
randomness. That is why the bias is stable across a page load rather than
averaging out.

## Why this produces the paper's result

The paper's first-segment definition (thesis 4.3.2) is a leg that is primary at
**both** endpoints when data transfer starts. Client primary comes from
`conflux_pick_first_leg()`, lowest RTT; exit primary comes from LowRTT, lowest
RTT. Both orderings are the same ordering of the same two paths. A guard that
lowers its RTT wins both at once, which is why the paper sees TPR go from 0.189
to 0.736 at a 128 ms advantage rather than something like a doubling.
