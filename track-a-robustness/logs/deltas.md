# Track A: deltas from the authors' setup

Every difference between their published configuration and what actually ran.
One row per deviation, added as it happens rather than reconstructed at the end.

| Date | Area | Theirs | Ours | Why |
|---|---|---|---|---|
| 2026-09-06 | Hardware | Single RTX 5090, Linux | Ryzen 9 5900HX, 16 threads, no CUDA GPU | The 5090 is in the other machine. Only k-FP has run so far and it is CPU-only by design, so this cost nothing yet. The four CNNs are not run here. |
| 2026-09-06 | World | Open world, π10 at r = 10, threshold tuned to maximize F1 | Closed world, macro F1 over the monitored classes | The real non-monitored background is DUA-gated and absent from OSF. See `osf-inventory.md`. **No number here is comparable to a number in their tables.** |
| 2026-09-06 | Code | "Analysis code released" | Reimplemented | Nothing on OSF, no repo found, and the 9.9 GB OSF archive zip contains data only. Draft email `docs/correspondence/01-code-availability.md` is still unsent. |
| 2026-09-06 | k-FP features | "Feature Vector: 175 (max)", Hayes & Danezis 2016 | 175-dimensional reimplementation, composition documented at the top of `src/kfp.py` | Their exact feature list is not printed in the thesis and their code is unavailable. Dimension matches; the individual features are not guaranteed to. |
| 2026-09-06 | k-FP classifier stage | Random forest, n_est = 1000, feature importances used | `RandomForestClassifier(n_estimators=1000)`, prediction taken directly | n_est matches Table C.1. k-FP proper turns RF leaves into fingerprints and runs k-NN for the open-world decision; with no open world there is nothing for that stage to do. Feature-importance selection not applied, since it exists to shrink the vector and we are not tuning. |
| 2026-09-06 | Label space | 112 sites nominal | Per-axis intersection: 103 classes cross-network, 106 drift | Sites disappear between collections. Six (16, 40, 60, 76, 95, 100) are gone from the UK month-6 set, and site 100 is already missing from AU month 0. Scoring against classes that cannot occur would depress recall for a reason unrelated to drift. |
| 2026-09-06 | Protocol | Train on the month-0 / AU collection, no in-distribution cell reported in the drift table beyond month 0 itself | 20% stratified holdout of the training collection per seed, reported as `in-dist` | Without an anchor, a cross-network or month-6 score is an absolute number rather than a degradation. Costs 20% of the training data, which is a real deviation. |
| 2026-09-06 | Seeds | Single runs | 3 seeds, sd reported | Required by the brief. |
| 2026-09-06 | DF architecture | Not published in the thesis, no code released | Reimplemented from Sirinam et al. CCS 2018: four conv blocks, filters 32/64/128/256, kernel 8, max pool 8 stride 4, ELU in block 1 then ReLU, dropouts 0.1 per block and 0.7 / 0.5 in the classifier, two 512 FC layers | Table C.1 pins the optimizer, batch, epochs and input length but not the network. 3.85M parameters. |
| 2026-09-06 | Tik-Tok validation split | "EarlyStop: val_loss patience=6", no split size given | 10% of the training portion, stratified, per seed, taken from the 80% fit set so the in-distribution anchor stays held out | Early stopping needs a validation set and the table does not size one. |
| 2026-09-06 | RF architecture | "2D CNN", TAM length 1800 | Reimplemented: four 2D conv blocks over the (2, slots) matrix, first kernel (2,8) collapsing the direction axis, pooling along time only | The weakest of the three reimplementations. Table C.1 gives the input and schedule but only "2D CNN" for the network, and Shen et al.'s exact architecture was not reproduced from the paper. |
| 2026-09-06 | TAM Tmax | "set dynamically to the highest trace load time, 42-47 s" | 45.0 s, measured: every collection in this repo caps at exactly 45.00 s | Matches their described procedure. At 1800 slots that is a 25 ms slot, finer than the 80 s default's 44 ms, and Appendix C.1 says fine slots are what break RF across networks. |
| 2026-09-06 | Holmes | Dual-branch CNN, Adam/AdamW, CrossEntropy + SupConLoss, temporal 1000 / TAF 2000 | **Not implemented, will be reported as not run** | Two branches, two optimizers and an unweighted loss mix is not enough to reimplement faithfully. An approximation would produce a number that looks like a measurement. |

## Matched deliberately, recorded so a later reader does not "fix" them

- Cross-network axis uses `pre-conflux/pre-month0-cfx0-{au,ca}.npz`. Thesis
  Table 4.1 is explicitly the pre-Conflux dataset.
- Drift axis uses the UK client, `post-month{0,2,6}-cfx0-uk.npz`. Thesis section
  4.2.9 states the longitudinal study is the UK vantage point. UK is also the
  only site with a month-2 cfx0 file.
- Traces used exactly as distributed: 5,000 cells, zero-padded, no truncation or
  resampling.

## Environment

- OS / kernel: Ubuntu 24.04.4 LTS, Linux 7.0.0-31-generic, native (not WSL)
- CPU: AMD Ryzen 9 5900HX, 8 cores / 16 threads, 30 GB RAM
- GPU: none usable. AMD Cezanne integrated only; no CUDA, no ROCm installed,
  and gfx90c is not a supported ROCm target.
- Python 3.12.3 in `.venv`; numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.0,
  matplotlib 3.11.1, torch 2.14.0+cpu.
- The CPU torch here is for verifying that the model code runs, not for
  producing results. Every CNN number must come from the GPU machine, and
  `run_torch.py` records `device` and `torch` in its JSON so the two cannot be
  confused later.
- Their code: not released. Nothing pulled.
- Data: 29 `.npz` from `osf.io/9m8ea`, 9.9 GB, all openly downloadable, all 29
  verified against the authors' `pre-sha512sum.txt` / `post-sha512sum.txt`
  (`src/verify_osf.py`, 29 ok / 0 bad / 0 missing). The DUA-gated open-world
  background set is not present and was not requested.
