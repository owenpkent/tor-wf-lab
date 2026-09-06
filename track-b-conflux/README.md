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

## Status, 2026-09-06

All five questions answered. Memo written: `../docs/track-b-memo.md`.

**Verdict: go**, on a narrowed project, conditional on a one-day kill test and
on asking the authors what they are already doing.

- Q2 did not kill it. Bounded reordering is already demonstrated inside Tor's
  own tree by `CONFLUX_ALG_CWNDRTT`, which turns out to be unreachable dead
  code, and only the first segment of a load needs de-biasing.
- Q5 did not kill it either, but it found the real risk: the paper's conclusion
  names this project as its own future work.
- The kill test is done, same day, and it passed: FS rate 0.448 with no
  advantage, 0.891 at 128 ms, 0.977 at 512 ms, detector validated at 1.0000 on
  single-leg control traces. See `notes/06-fs-kill-test.md` and
  `results/fs-rate.png`.
- A follow-up measured what ownership is worth instead of inferring it
  (`notes/07-fs-value-measured.md`): k-FP gets 0.744 of first-segment traces
  right against 0.374 of the rest, and 128 ms of advantage multiplies ownership
  by 1.97 but per-trace accuracy on owned traces by only 1.19. Ownership is the
  attack.
- Shadow is built here and the validation ran: unpatched tor 0.4.9.11 splits a
  download 0.512 between two identical guards and 0.71 to a guard with a 64 ms
  advantage (`notes/09-shadow-validation.md`). Harness in `shadow/`.
- Next action is the authors question in `../docs/correspondence/01`, then
  candidate B: make `CONFLUX_ALG_CWNDRTT` reachable and rerun the same sweep.
