Finished writeups land here.

- **Track A**, `track-a-robustness-axes.md`. Are network-mismatch and
  temporal-drift robustness distinct axes? Five classifiers, both axes, 3 seeds,
  closed world. Verdict: no classifier is good at both, but the independence
  claim rests almost entirely on RF. Numbers, figure and the slot-size sweep
  live in `../track-a-robustness/results/`.
- **Track B**, `track-b-memo.md`. Is Conflux scheduling that mitigates LowRTT
  latency bias a viable multi-week project? Verdict: go, narrowed to de-biasing
  which leg carries the start of a page load. Backed by three measurements the
  scoping brief did not ask for: the mechanism confirmed on the open traces,
  what first-segment ownership is worth, and stock tor reproducing the bias in
  Shadow. Notes and figures in `../track-b-conflux/`.
- `correspondence/`, drafts to the authors. **Send
  `03-combined-request.md`**, which supersedes drafts 01 and 02: it asks for the
  DUA-gated background set, the analysis code, and whether anyone is already
  working on the Conflux scheduling follow-up. Nothing has been sent.
