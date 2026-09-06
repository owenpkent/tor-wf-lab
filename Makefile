# Reproduction targets. Every one of these was run to produce what is in
# results/; none of them invents a number.
#
# The data is not in the repo: 9.9 GB of monitored traces from osf.io/9m8ea,
# openly downloadable and sha512-verified against the authors' own lists.

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
A    := track-a-robustness
B    := track-b-conflux

.PHONY: help venv data verify kfp fs fs-figure figures clean-figures

help:
	@echo "make venv       create .venv and install the analysis stack"
	@echo "make fs-figure  end to end: fetch 1.7 GB, measure, plot $(B)/results/fs-kfp.png"
	@echo "make data       fetch all 29 open .npz (9.9 GB) and verify checksums"
	@echo "make kfp        k-FP on both Track A axes, 3 seeds (needs 'make data')"
	@echo "make fs         Track B first-segment sweep and its two measurements"
	@echo "make figures    redraw every figure from the JSON already in results/"
	@echo
	@echo "The four CNNs are not here: see $(A)/RUNBOOK-5090.md. Shadow is not"
	@echo "here either: see $(B)/shadow/ and notes/09-shadow-validation.md."

$(VENV):
	python3 -m venv $(VENV) && $(PIP) install -q -r requirements.txt

venv: $(VENV)

# One command, one figure, from nothing. Downloads the six latency-sweep
# collections (~1.7 GB), measures what first-segment ownership is worth, plots.
fs-figure: venv
	$(PY) $(A)/src/fetch_osf.py post-month2-cfx2-ca.npz post-month2-cfx2-ca-rtt-
	$(PY) $(B)/src/run_fs_kfp.py
	$(PY) $(B)/src/plot_fs_kfp.py

data: venv
	$(PY) $(A)/src/fetch_osf.py
	$(PY) $(A)/src/verify_osf.py

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
