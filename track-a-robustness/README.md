# Track A: robustness axes

Brief: `../prompts/prompt-a-robustness-axes.md`.

Hypothesis under test: network-mismatch robustness and temporal-drift
robustness are distinct properties, and no current WF classifier has both.
Classifiers in scope: k-FP, DF, Tik-Tok, RF, Holmes.

Gate order, from the brief. Do not skip ahead of a failed gate.

1. **OSF inventory.** Report open vs DUA-gated before running anything. If the
   open synthetic traces cannot support both axes, say so and propose the
   closest feasible substitute.
2. **Their code running**, published hyperparameters only (Appendix A Table 7).
3. **Reproduce one paper number** as a sanity check. Name which one and how
   close. Not within a few points means stop and report.
4. **Both axes, 3+ seeds**, variance reported.
5. **One scatter plot**: cross-network F1 against six-month (or longest
   available gap) F1, one point per classifier, error bars.

Steps 1 and 3 are the real gates. Most of the ways this weekend goes wrong are
discovering at step 4 that the data never supported the question.
