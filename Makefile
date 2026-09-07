# Reproduction targets. Every one of these was run to produce what is in
# results/; none of them invents a number.
#
# The data is not in the repo: 29 .npz of monitored traces, 10.6 GB, openly
# downloadable from osf.io/9m8ea. Sizes throughout are decimal GB, matching what
# curl and OSF report. Every target that downloads also verifies, against the
# authors' own sha512 lists; a bad or absent digest fails the target.

VENV  := .venv
STAMP := $(VENV)/.stamp
PY    := $(VENV)/bin/python
PIP   := $(VENV)/bin/pip
A     := track-a-robustness
B     := track-b-conflux

.PHONY: help venv data verify kfp fs fs-figure figures clean-figures

help:
	@echo "make venv         create .venv and install the pinned analysis stack"
	@echo "make fs-figure    end to end: fetch 1.7 GB, verify, measure, plot $(B)/results/fs-kfp.png"
	@echo "make data         fetch all 29 open .npz (10.6 GB) and verify every one"
	@echo "make verify       re-check whatever is already in $(A)/data/"
	@echo "make kfp          k-FP on both Track A axes, 3 seeds (needs 'make data')"
	@echo "make fs           Track B first-segment sweep and its two measurements"
	@echo "make figures      redraw every figure from the JSON already in results/"
	@echo "make clean-figures  delete the four generated PNGs"
	@echo
	@echo "The four CNNs are not here: see $(A)/RUNBOOK-5090.md. Shadow is not"
	@echo "here either: see $(B)/shadow/ and notes/09-shadow-validation.md."

# A stamp file rather than the directory itself: a bare directory target is
# already up to date the moment .venv exists, so editing requirements.txt would
# never reinstall and a .venv made before this file existed would never be
# brought up to the pins.
$(STAMP): requirements.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install -q -r requirements.txt
	touch $@

venv: $(STAMP)

# One command, one figure, from nothing. Downloads the six latency-sweep
# collections (1.7 GB), verifies them, measures what first-segment ownership is
# worth, plots. fetch_osf.py always pulls the sha512 listings too, so the verify
# step here has something to check against.
fs-figure: venv
	$(PY) $(A)/src/fetch_osf.py post-month2-cfx2-ca.npz post-month2-cfx2-ca-rtt-
	$(PY) $(A)/src/verify_osf.py
	$(PY) $(B)/src/run_fs_kfp.py
	$(PY) $(B)/src/plot_fs_kfp.py

data: venv
	$(PY) $(A)/src/fetch_osf.py
	$(PY) $(A)/src/verify_osf.py --require-all

verify: venv
	$(PY) $(A)/src/verify_osf.py

kfp: venv
	$(PY) $(A)/src/run_kfp.py

fs: venv
	$(PY) $(B)/src/run_fs_sweep.py
	$(PY) $(B)/src/run_fs_kfp.py

figures: venv
	$(PY) $(B)/src/plot_fs.py
	$(PY) $(B)/src/plot_fs_kfp.py
	$(PY) $(B)/shadow/plot_shadow.py
	$(PY) $(A)/src/plot_axes.py

clean-figures:
	rm -f $(B)/results/fs-rate.png $(B)/results/fs-kfp.png \
	      $(B)/results/shadow-sweep.png $(A)/results/axes.png
