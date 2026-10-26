# Legacy components

The files in this folder are earlier iterations of the detection pipeline,
kept for history and reference. They are **not** part of the current
pipeline and are not required to reproduce the results described in the
paper or the top-level README.

| File | What it was | Superseded by |
|---|---|---|
| `train_model.py` | Stage 2 classifier using a Random Forest trained directly on cluster output with `sus`/`evil` as the label. | `train_xgboost.py`, which trains an XGBoost classifier specifically on the anomaly clusters and tracks precision/recall/ROC-AUC. |
| `mcp_wrapper_phase2.py` | A wrapper that loaded the Random Forest model above plus a separate `IsolationForest` risk-scoring step, driven by `data/config.json`. | The combined HDBSCAN → XGBoost pipeline (`clustering.py`, `train_xgboost.py`, `prometheus_exporter_xgboost.py`). |
| `grafana_dashboard_phase2.json` | Grafana dashboard matching the Random Forest exporter (`prometheus_exporter_phase2.py`, which no longer exists in this repo). | `monitoring/grafana_dashboard_xgboost.json`. |

If you're trying to reproduce the paper's results, use the root-level
scripts and `monitoring/grafana_dashboard_xgboost.json` instead — these
files are intentionally excluded from `scripts/` and the main README's
quick-start instructions.
