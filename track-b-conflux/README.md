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
- It also moved the design target. The advantaged guard wins the first segment
  more often *and* keeps more of the load after winning, so a policy that only
  randomizes the first leg addresses half the effect.
- Next action is the authors question in `../docs/correspondence/01`, then
  candidate B: make `CONFLUX_ALG_CWNDRTT` reachable and measure it.
