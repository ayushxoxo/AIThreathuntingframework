# AI Threat Hunting — Behavioral Anomaly Detection for SIEM Blindspots

A two-stage security analytics pipeline: unsupervised behavioral clustering
(HDBSCAN) finds the events that don't look like normal activity, then a
supervised classifier (XGBoost) scores those events for risk. Results are
exported to Prometheus and visualized in Grafana.

This repository is the reference implementation for the proof-of-concept
described in **"Towards Detecting the Undetectable: AI Techniques for
Identifying Blindspots in Security Monitoring Systems"** (Nidhi Sharma and
Ayush Sharma). The headline numbers in that paper's Table I — 3.8M events,
378 clusters, 566,101 anomalies, 22,446 high-risk candidates — were produced
by the scripts in this repo, run against the BETH cybersecurity dataset.
The summary files under `results/` are the actual output of that run.

## What this is, and isn't

This is a research prototype, not a hardened production tool. A few things
worth knowing before you dig in:

- The raw dataset and trained model files are **not** included in this repo
  (see [Dataset](#dataset) below) — you need your own copy to reproduce a
  run end to end.
- The classifier's precision/recall/F1/ROC-AUC from the original run were
  not retained — only the clustering-stage summary survived. `docs/PHASE2_XGBOOST.md`
  documents *target* thresholds the classifier was designed against, not
  confirmed results. Re-running `train_xgboost.py` on your own copy of the
  data will print real numbers.
- `demo/demo_timeseries.py` exists only to put a moving line on a Grafana
  panel for live demos. Every number it emits is `random.randint()`. It is
  not wired into the real exporter — see the warning at the top of that file.
- `legacy/` holds an earlier Random Forest + Isolation Forest version of
  the pipeline, kept for history. It isn't used by anything in this repo.

## Architecture

```
Raw logs (CSV)
      │
      ▼
Stage 1 — Preprocessing + HDBSCAN clustering (per host)
      │     preprocessing.py, clustering.py, run_clustering.py
      ▼
Stage 2 — XGBoost classification of anomaly clusters
      │     train_xgboost.py
      ▼
Monitoring — Prometheus exporter
      │     prometheus_exporter_xgboost.py  (port 8001)
      ▼
Prometheus (port 9090)  →  Grafana (port 3000)
```

Stage 1 groups each host's events into behavioral clusters with HDBSCAN and
sets aside whatever doesn't fit a stable cluster (label `-1`) as anomalous.
Stage 2 trains an XGBoost classifier on those anomalous events — labeled
with the dataset's own `sus`/`evil` fields — to separate benign outliers
from likely-malicious ones, and buckets predictions into risk tiers. The
exporter re-runs inference on a timer and publishes the counts Grafana
graphs.

## Repository layout

```
.
├── preprocessing.py              # feature cleaning, encoding, scaling, PCA/UMAP
├── clustering.py                 # HDBSCAN wrapper + cluster-file export
├── run_clustering.py             # Stage 1 entry point
├── experiments.py                # sweeps 4 clustering configs for comparison
├── train_xgboost.py              # Stage 2 entry point
├── prometheus_exporter_xgboost.py# live inference → Prometheus metrics (port 8001)
├── clustering_config.json        # Stage 1 configuration
├── requirements.txt
├── demo/
│   └── demo_timeseries.py        # SYNTHETIC data for a demo panel — see warning in file
├── docs/
│   ├── ARCHITECTURE.md           # file-by-file breakdown and data flow
│   ├── CLUSTERING_GUIDE.md       # Stage 1 tuning guide
│   ├── PHASE2_XGBOOST.md         # Stage 2 training/evaluation notes
│   └── GRAFANA_DASHBOARD_GUIDE.md
├── monitoring/
│   └── grafana_dashboard_xgboost.json
├── results/
│   ├── clustering_summary.json          # the run behind the paper's Table I
│   └── clustering_summary_by_host.csv
├── scripts/
│   ├── setup_venv.bat
│   ├── activate_venv.bat
│   ├── start_all.bat              # exporter + Prometheus + Grafana
│   └── stop_all.bat
└── legacy/                        # superseded Random Forest pipeline, kept for history
```

`data/` is intentionally absent from the repo (see below) and is created
locally by you.

## Dataset

The pipeline expects the BETH cybersecurity dataset (or any structured log
CSV with comparable fields — `hostName`/host identifier, `sus`, `evil`, and
behavioral/process attributes) as a single CSV at:

```
data/merged_output1.csv
```

The dataset is not redistributed in this repo. Download it separately and
place it at that path before running Stage 1.

## Setup

Requires Python 3.10+.

```bash
python -m venv venv
venv\Scripts\activate          # scripts\activate_venv.bat does this for you
pip install -r requirements.txt
```

`umap-learn` is optional — only needed if you set `dimensionality_reduction.mode`
to `"umap"` in `clustering_config.json` (default is `"pca"`, which has no
extra dependency).

## Running the pipeline

**Stage 1 — clustering:**

```bash
python run_clustering.py
```

Reads `clustering_config.json`, auto-detects hosts, clusters each one
independently with HDBSCAN, and writes:

- `data/clusters/normal/host_<id>_cluster_<label>.csv` — one file per stable cluster
- `data/clusters/anomaly/host_<id>_cluster_-1.csv` — anomalous events (cluster `-1`)
- `results/clustering_summary.json` and `results/clustering_summary_by_host.csv`

See `docs/CLUSTERING_GUIDE.md` for parameter tuning (target anomaly rate,
PCA vs. UMAP, distance metric, etc.) and `experiments.py` to sweep multiple
configurations at once.

**Stage 2 — classification:**

```bash
python train_xgboost.py
```

Loads every file under `data/clusters/anomaly/` across all hosts, builds a
binary label (`sus == 1 OR evil == 1`), trains an XGBoost classifier, prints
a classification report / confusion matrix / ROC-AUC, and saves:

- `data/xgboost_threat_classifier.json`
- `data/xgboost_feature_names.pkl`
- `data/xgboost_metadata.json`

It also copies any event confirmed malicious (`evil == 1`) out to
`data/clusters/malicious/malicious_logs.csv`, which the exporter reads
alongside `normal/` and `anomaly/` for its system-wide counts.

See `docs/PHASE2_XGBOOST.md` for the target evaluation thresholds and risk-tier
definitions.

## Monitoring stack

```bash
python prometheus_exporter_xgboost.py     # serves real metrics on :8001/metrics
```

`scripts/start_all.bat` will also try to start a local Prometheus and
Grafana instance for you — it assumes they're unzipped as sibling folders
next to this repo (edit the two path variables at the top of the script if
yours live elsewhere, or just point your own Prometheus at `127.0.0.1:8001`).
Import `monitoring/grafana_dashboard_xgboost.json` into Grafana and see
`docs/GRAFANA_DASHBOARD_GUIDE.md` for the panel layout. `scripts/stop_all.bat`
tears everything back down.

## Results

`results/clustering_summary_by_host.csv` is the per-host output from the run
cited in the paper: 17 hosts, ~3.8M events, 378 total clusters (361 normal +
17 anomalous), 566,101 anomalous events (≈15%). These are cross-checked
against the paper's Table I and match exactly.

## Citing this work

If you build on this, please cite the paper:

> N. Sharma and A. Sharma, "Towards Detecting the Undetectable: AI
> Techniques for Identifying Blindspots in Security Monitoring Systems."

## Contact

- Nidhi Sharma — nidhi.1.sharma@jci.com
- Ayush Sharma — ayush.3.sharma@jci.com
