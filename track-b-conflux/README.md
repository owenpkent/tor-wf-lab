# Track B: Conflux scheduling scoping

Brief: `../prompts/prompt-b-conflux-scheduling.md`. Output is a memo in
`../docs/`, not code. No Tor patches this session.

Question order matters, and questions 2 and 5 are both kill switches:

1. LowRTT primary-leg selection: how it picks, where the code lives, what state
   it depends on.
2. **Crux.** Can a lower-latency-bias policy exist without giving up the
   congestion and head-of-line-blocking wins Conflux exists for? If every
   evener-spreading policy reintroduces head-of-line blocking, the project is
   dead.
3. Two or three candidate policies, a paragraph each, with the tradeoff named.
4. Can Shadow evaluate these? Minimal experiment, what it must model, setup
   time.
5. **Prior art.** tor-dev, Tor GitLab issues, recent literature. Already in
   progress is a no-go.

Cheapest order in practice is 5 then 2, since either one alone kills it. Answer
them in the brief's order in the memo regardless.

Notes go in `notes/`, one file per question.

## Status: done, verdict go

Memo: `../docs/track-b-memo.md`. All five brief questions answered, and three
measurements the brief did not ask for but which the answers rested on.

**Verdict: go**, narrowed to de-biasing which leg carries the start of a page
load, conditional on asking the authors whether they are already doing it
(`../docs/correspondence/03-combined-request.md`, unsent).

## What is here

```
notes/01-lowrtt-mechanics.md      Q1. How LowRTT picks the primary leg, with file:line
notes/02-crux-hol-tradeoff.md     Q2. The crux. Survives: reorder can be bounded
notes/03-candidate-policies.md    Q3. Three policies and the tradeoff each makes
notes/04-shadow-evaluation.md     Q4. What a Shadow experiment would need
notes/05-prior-art.md             Q5. Unclaimed, but the authors named it as their future work
notes/06-fs-kill-test.md          Mechanism confirmed on open traces
notes/07-fs-value-measured.md     What ownership is worth, measured not inferred
notes/08-shadow-feasibility.md    Shadow builds and runs on this machine
notes/09-shadow-validation.md     Stock tor reproduces the bias in simulation
src/                              FS detector, the two trace measurements, plots
shadow/                           experiment generator, pcap analysis, the sweep
results/                          JSON and figures for all three measurements
```

## The three measurements, in one place

| | Result |
|---|---|
| Ownership vs latency (real traces) | 0.448 with no advantage, 0.891 at 128 ms, 0.977 at 512 ms. Detector validated at 1.0000 on single-leg controls |
| What ownership is worth (real traces) | k-FP gets 0.744 of first-segment traces right against 0.374 of the rest. Advantage buys ownership x1.97, accuracy on owned traces only x1.19 |
| Stock tor in Shadow | Two identical guards split a download 0.512; a 64 ms advantage takes 0.71. Byte share plateaus near 0.78, LowRTT's cwnd fallback |

Ownership and byte share are different quantities and saturate differently, at
0.977 and 0.78. They are not interchangeable numbers.

## Reproducing

`src/` runs against the OSF traces staged for Track A, no GPU needed. `shadow/`
needs Shadow, tgen and tor 0.4.8+ on PATH, and `SHADOW_TOR_EXAMPLE` pointing at
a Shadow checkout's `examples/docs/tor`. A 30-simulated-minute run takes about
7 seconds; the 60-run sweep took under ten minutes.

## Next, if the project goes ahead

Candidate A (randomise the initial leg) as the shippable change, candidate B
(CWNDRTT over the first segment) to get below Conflux's residual leak, then the
same Shadow sweep against the patched tor: the difference is the defense's
effect and tgen's stream timings are the time-to-first-byte cost, from one run.
