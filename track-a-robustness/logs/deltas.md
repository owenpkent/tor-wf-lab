# Track A: deltas from the authors' setup

Every difference between their published configuration and what actually ran.
One row per deviation, added as it happens rather than reconstructed at the end.

| Date | Area | Theirs | Ours | Why |
|---|---|---|---|---|
| 2026-09-06 | Hardware | Single RTX 5090, Linux | Ryzen 9 5900HX, 16 threads, no CUDA GPU | The 5090 is in the other machine. Only k-FP has run so far and it is CPU-only by design, so this cost nothing yet. The four CNNs are not run here. |
| 2026-09-06 | World | Open world, π10 at r = 10, threshold tuned to maximize F1 | Closed world, macro F1 over the monitored classes | The real non-monitored background is DUA-gated and absent from OSF. See `osf-inventory.md`. **No number here is comparable to a number in their tables.** |
| 2026-09-06 | Code | "Analysis code released" | Reimplemented | Nothing on OSF, no repo found, and the 10.6 GB OSF archive zip contains data only. Draft email `docs/correspondence/01-code-availability.md` is still unsent. |
| 2026-09-06 | k-FP features | "Feature Vector: 175 (max)", Hayes & Danezis 2016 | 175-dimensional reimplementation, composition documented at the top of `src/kfp.py` | Their exact feature list is not printed in the thesis and their code is unavailable. Dimension matches; the individual features are not guaranteed to. |
| 2026-09-06 | k-FP classifier stage | Random forest, n_est = 1000, feature importances used | `RandomForestClassifier(n_estimators=1000)`, prediction taken directly | n_est matches Table C.1. k-FP proper turns RF leaves into fingerprints and runs k-NN for the open-world decision; with no open world there is nothing for that stage to do. Feature-importance selection not applied, since it exists to shrink the vector and we are not tuning. |
| 2026-09-06 | Label space | 112 sites nominal | Per-axis intersection: 103 classes cross-network, 106 drift | Sites disappear between collections. Six (16, 40, 60, 76, 95, 100) are gone from the UK month-6 set, and site 100 is already missing from AU month 0. Scoring against classes that cannot occur would depress recall for a reason unrelated to drift. |
| 2026-09-06 | Protocol | Train on the month-0 / AU collection, no in-distribution cell reported in the drift table beyond month 0 itself | 20% stratified holdout of the training collection per seed, reported as `in-dist` | Without an anchor, a cross-network or month-6 score is an absolute number rather than a degradation. Costs 20% of the training data, which is a real deviation. |
| 2026-09-06 | Seeds | Single runs | 3 seeds, sd reported | Required by the brief. |
| 2026-09-06 | DF architecture | Not published in the thesis, no code released | Sirinam et al., CCS 2018, Table 10: filters 32/64/128/256, kernel 8, pool 8 stride 4, ELU in block 1 then ReLU, dropout 0.1 per block, FC 512/512 with dropout 0.7/0.5 | Supersedes the CPU-prep version. Keras `same` pooling is asymmetric and right-heavy and PyTorch cannot express it with a symmetric pad, so it is emulated explicitly in `_keras_same_pool`. This matters: a symmetric `padding=2` gives 1250 -> 312 -> 78 -> 19 and a flatten of 4,864, while Keras gives 1250 -> 313 -> 79 -> 20 and the paper's **5,120**. Every DF and Tik-Tok number here used 5,120. |
| 2026-09-06 | Tik-Tok validation split | "EarlyStop: val_loss patience=6", no split size given | 10% of the training portion, stratified, per seed | Unchanged from the CPU-prep plan. Taken from the 80% fit set so the in-distribution anchor stays held out; best val_loss weights are restored before evaluation. |
| 2026-09-06 | RF architecture | "2D CNN", TAM length 1800 | Transcribed from the RF authors' own released code, `robust-fingerprinting/RF`, `RF/models/RF.py` | Supersedes the CPU-prep version, which its own delta row called "the weakest of the three reimplementations". The real network is a 2D front-end, then a reshape `(B,64,1,W) -> (B,32,2W)`, then a 1D VGG stack whose final convolution emits one channel per class into a global average pool. There is **no fully connected layer**. Two published quirks are reproduced rather than fixed: that channel-mixing reshape, and BatchNorm+ReLU after the class-emitting convolution, which leaves the pooled logits non-negative before CrossEntropy. Being fully convolutional, it is also slot-agnostic, so the sweep needs no resizing. |
| 2026-09-06 | TAM Tmax and binning | "set dynamically to the highest trace load time, 42-47 s" | Tmax = 45.0 s measured; binning `idx = int(t*(N-1)/Tmax)` per their released code, so the slot is Tmax/(N-1) | Supersedes the CPU-prep version, which used Tmax/N. The distinction is confirmed against the thesis: their default Tmax = 80 under the (N-1) formula gives 44.5 ms, which is the "roughly 44 ms" the thesis quotes. At Tmax = 45, N = 1800 the slot is 25.01 ms. Packets at or past Tmax accumulate in the final slot rather than being dropped. |
| 2026-09-06 | Holmes | Dual-branch CNN, Adam/AdamW, CrossEntropy + SupConLoss, temporal 1000 / TAF 2000 | **Implemented and run**, reversing the earlier "not run" decision | That decision rested on Table C.1 being too thin to reimplement faithfully. The premise is wrong: the authors' complete code is public in WFlib (`FIND-Lab/Website-Fingerprinting-Library`, branch `master`), so nothing had to be guessed. Table C.1's Holmes column is also not one dual-branch network; the slash-separated pairs are two separate models in a four-stage pipeline. Detail in the Holmes rows below. |

| 2026-09-06 | Hardware (CNNs) | Single RTX 5090, Linux | RTX 5090 32 GB, Windows 11 native, no WSL | The 5090 box has no WSL installed. Native Windows CUDA wheels work on Blackwell, so WSL2 was not installed just to match the OS. torch 2.11.0+cu128, CUDA 12.8, driver 610.88, compute capability (12, 0) confirmed before any run. |
| 2026-09-06 | Tik-Tok architecture | Not released | Same network as DF, input direction x timestamp | Rahman et al., PoPETs 2020 state Tik-Tok is DF on directional timing. Shares `DFNet`. |
| 2026-09-06 | Determinism | Not discussed | `cudnn.benchmark = True`, seeds set for torch and numpy | Non-deterministic kernel selection is accepted; seed-to-seed variance is reported and is the quantity of interest, so bitwise reproducibility was not bought at the cost of speed. |
| 2026-09-06 | Holmes, what it even is | Table C.1 row: "dual-branch CNN", temporal 1000 / TAF 2000, Adam / AdamW, CrossEntropy / SupConLoss, batch 200 / 256 | A four-stage pipeline containing two separate models, transcribed from the authors' released code | Table C.1's Holmes column is not one network with two branches. The slash-separated pairs are two different models: an auxiliary CNN on the 1000-bin temporal feature (CrossEntropy, Adam, batch 200) used only to compute attributions, and the Holmes encoder itself on TAF (SupConLoss, AdamW, batch 256). Reading the table as a single dual-branch net, as the runbook did, would have produced something that is not Holmes. Source: `FIND-Lab/Website-Fingerprinting-Library` (WFlib) branch `master`, `WFlib/models/Holmes.py`, `WFlib/tools/data_processor.py`, `exp/data_analysis/{feature_attr,spatial_analysis}.py`, `exp/dataset_process/data_augmentation.py`, `scripts/Holmes.sh`. |
| 2026-09-06 | Holmes prediction | Not described in the thesis | Per-class centroid + MAD radius from the augmented validation set, predict argmin(cosine distance - radius) | The Holmes network emits a 128-d embedding and has no classifier head, so it cannot predict at all without this calibration step. It is part of their pipeline, not post-processing we added. |
| 2026-09-06 | Holmes temporal feature | `for packet in X[idx]: if packet == 0: break` over direction*timestamp | Padding detected by direction == 0 instead | Every trace in this dataset has its first packet at exactly t = 0.0, so direction*timestamp is 0 there and their loop would break on the first packet and return an all-zero feature for all 20,660 traces. The break exists to stop at padding; testing direction preserves that intent. Without this the whole Holmes pipeline silently trains on zeros. |
| 2026-09-06 | Holmes validation split | Ships separate train/valid files | 15% of the training portion, stratified, per seed | Needed by three stages (attribution, best-epoch selection, centroid calibration). Sized at 15% rather than 10% because their attribution code asserts at least 12 samples per class; 15% gives a minimum of 14 and a median of 25. Taken from the training portion, never from the in-distribution holdout. |
| 2026-09-06 | Holmes feature extraction | Per-trace Python loops, 30 process workers | Vectorised numpy, single process | Verified equal, not assumed: both TAF and the temporal feature were checked against literal transcriptions of their `process_TAF` / `agg_interval` / `extract_temporal_feature` loops on real traces, max absolute difference 0.0 on all three TAF rows. Their `np.searchsorted` binning is reproduced in closed form, which is valid because timestamps are monotonic within a trace here (checked on all 20,660). |
| 2026-09-06 | Holmes attribution batching | 10 attributed samples in one DeepLiftShap call | Same 10 samples in chunks of 2, summed | Purely to bound activation memory; DeepLiftShap expands each input against all 206 baselines, and the sum over samples is what their code keeps, so the result is identical. Background and attributed sample selection is unchanged (first 2 per class as background, next 10 as attributed). |
| 2026-09-06 | Holmes dependencies | captum, pytorch-metric-learning | captum 0.9.0, pytorch-metric-learning 2.9.0 | SupConLoss is theirs (`losses.SupConLoss(temperature=0.1)`), not reimplemented. |
| 2026-09-06 | Effective training set size | Not discussed | k-FP / DF / RF fit on all 16,528; Tik-Tok on 14,875; Holmes on 14,048 | Every classifier gets the identical 80/20 split, so the in-distribution anchor and all test cells are the same data for all five. But Tik-Tok's early stopping and Holmes's pipeline both need a validation set, and taking it from the training portion (rather than the anchor) means those two fit on 10% and 15% less data respectively. This follows from comparing published configurations rather than from a choice we made, but it slightly disadvantages Tik-Tok and Holmes and should not be read as an architectural difference. |

| 2026-09-06 | Holmes attribution, rare classes | `assert bg_test_X.shape[0] >= 12`, i.e. 2 background plus 10 attributed samples per class | 2 background always, up to 10 attributed, fewer for classes that cannot supply them | The drift axis is rarer-tailed than their datasets: its scarcest class has 74 traces in the training collection, so a 15% validation split yields 9 and their assert fails. The two alternatives were worse. Enlarging the validation split to 25% would clear the floor but cost Holmes a quarter of its training data that the other four classifiers keep, confounding exactly the comparison being made; topping up from the fit set would attribute over samples the model trained on. Attributing over fewer samples only makes that class's cumulative curve noisier, and the curve is used solely to pick a coarse truncation percentage band. Affected classes are logged per run. |

| 2026-09-06 | Network pairs | One pair, AU -> CA on the pre-Conflux dataset (Table 4.1) | Four ordered pairs added on post-Conflux month 0: AU->CA, AU->UK, UK->AU, UK->CA | The thesis measures "network-mismatch robustness" at a single point, so it cannot separate a property of a classifier from a property of that country pair. Post-Conflux month 0 is the only collection where AU, CA and UK were gathered together. These cells are a different dataset from the main cross-network axis and are **not** comparable to it cell for cell; the comparison that matters is between cells within each axis. Results in `results/netpairs/`. |
| 2026-09-06 | Holmes attribution, unattributable classes | `assert >= 12` per class | Classes that cannot supply 2 background plus 1 attributed sample are skipped, and take the median effective range over the classes that could | The post-Conflux AU collection has a class with 10 traces in total, so its validation share is 1. The effective range only sets the truncation window used to augment that class, and the median over the other 110 classes is a better estimate than any fixed constant. Skipped classes are logged per run. |

| 2026-09-06 | Vantage confound | Table 4.1 trains AU and tests across networks; Table 4.3 trains UK and tests across time | Added `vantage-au`: one training collection, one anchor, one label space, with both network cells and the drift cell scored against it | The thesis's two axes do not share a training collection, and AU-trained models degrade about 2.9x more in general, so vantage and axis are entangled in its comparison and in ours. This axis removes the confound. It is an addition, not a replacement: the main table still follows the thesis's own design so the numbers stay traceable to theirs. Results in `results/vantage/`. |

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
- Data: 29 `.npz` from `osf.io/9m8ea`, 10.6 GB, all openly downloadable, all 29
  verified against the authors' `pre-sha512sum.txt` / `post-sha512sum.txt`
  (`src/verify_osf.py`, 29 ok / 0 bad / 0 missing). The DUA-gated open-world
  background set is not present and was not requested.

## Environment, the 5090 machine (all CNN runs)

- OS: Windows 11 Pro 10.0.26200, native. WSL2 is not installed and was not
  required; the CUDA wheels for Blackwell work under native Windows Python.
- GPU: NVIDIA GeForce RTX 5090, 32 GB, driver 610.88, CUDA UMD 13.3.
- Python 3.12.10, `.venv`; torch 2.11.0+cu128, CUDA runtime 12.8.
  `torch.cuda.get_device_capability()` returns `(12, 0)` and `sm_120` is in
  `torch.cuda.get_arch_list()`, checked before any training run.
- Data: the five files the two axes need, extracted from the bulk OSF archive
  `9m8ea-osfstorage-archive.zip` rather than re-downloaded, then verified with
  `src/verify_osf.py`: 5 ok, 0 bad, 24 missing (the 24 are the other open files,
  not needed here). The DUA-gated background set is still absent.
- All input tensors are resident on the GPU for the whole run; the TAM is built
  once per collection, not per seed.
