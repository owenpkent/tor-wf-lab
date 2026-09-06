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
- Next action is not code. It is the one-day first-segment-detector check on the
  open `-rtt-*` OSF files, described in section 6 of the memo.
