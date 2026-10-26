# 🎯 Phase 2: XGBoost Threat Classification

## Overview
Supervised classification using XGBoost to separate suspicious/malicious logs from benign logs in anomaly clusters.

---

## Architecture

```
Anomaly Clusters (All Hosts)
    ↓
Load & Merge
    ↓
Create Target: sus=1 OR evil=1
    ↓
Preprocess Features
    ↓
Train XGBoost (400 estimators)
    ↓
Predict Probabilities
    ↓
Export to Prometheus
```

---

## Quick Start

### Step 1: Train XGBoost Model

```bash
python train_xgboost.py
```

**Output:**
- `data/xgboost_threat_classifier.json` - Trained model
- `data/xgboost_feature_names.pkl` - Feature list
- `data/xgboost_metadata.json` - Model metadata

**Expected:**
- Training on ~14% positive class (sus OR evil)
- ROC-AUC > 0.85
- Recall > 0.80

---

### Step 2: Start Prometheus Exporter

```bash
python prometheus_exporter_xgboost.py
```

**Endpoint:** http://localhost:8001/metrics

**Metrics Exposed:**
```
xgb_anomaly_total              # Total anomaly logs
xgb_predicted_malicious_total  # Predicted malicious
xgb_predicted_benign_total     # Predicted benign
xgb_high_risk_total            # Probability ≥ 0.8
xgb_suspicious_total           # Probability 0.5-0.8
xgb_avg_probability            # Average risk score
```

---

## Target Definition

**Broader Detection Model:**
```python
label = (sus == 1) OR (evil == 1)
```

- **1**: Suspicious or malicious
- **0**: Benign

**Expected Distribution:**
- Positive class: ~14%
- Negative class: ~86%

---

## XGBoost Configuration

```python
XGBClassifier(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=auto,  # Computed dynamically
    tree_method='hist',
    eval_metric='logloss'
)
```

---

## Risk Tiers

| Probability | Tier | Action |
|-------------|------|--------|
| ≥ 0.8 | High Risk | Immediate alert |
| 0.5 - 0.8 | Suspicious | Investigation |
| < 0.5 | Low Risk | Monitor |

---

## Data Flow

### Training
1. Load all files under `data/clusters/anomaly/`
2. Merge across all hosts
3. Create binary target (sus OR evil)
4. Remove non-numeric features
5. Train XGBoost with stratified split
6. Evaluate: Recall, F1, ROC-AUC
7. Save model

### Prediction (Prometheus)
1. Load anomaly clusters
2. Preprocess features
3. Predict probabilities
4. Calculate risk tiers
5. Update Prometheus metrics
6. Repeat every 15 seconds

---

## Evaluation Metrics

### Priority Metrics
- **Recall**: Detect as many threats as possible
- **F1-Score**: Balance precision and recall
- **ROC-AUC**: Overall discrimination ability

### Expected Performance
- Recall: > 0.80
- F1-Score: > 0.75
- ROC-AUC: > 0.85

---

## Prometheus Integration

### Configure Prometheus

Edit `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: "xgboost_exporter"
    scrape_interval: 15s
    static_configs:
      - targets: ["127.0.0.1:8001"]
```

### Query Examples

```promql
# Total malicious predictions
xgb_predicted_malicious_total

# High-risk events
xgb_high_risk_total

# Average risk probability
xgb_avg_probability

# Malicious rate
xgb_predicted_malicious_total / xgb_anomaly_total
```

---

## Grafana Dashboard

### Panel 1: Threat Classification
- **Type:** Pie Chart
- **Query:** `xgb_predicted_malicious_total` vs `xgb_predicted_benign_total`

### Panel 2: Risk Distribution
- **Type:** Bar Chart
- **Queries:**
  - `xgb_high_risk_total`
  - `xgb_suspicious_total`

### Panel 3: Average Risk Score
- **Type:** Gauge
- **Query:** `xgb_avg_probability`
- **Thresholds:** 0-0.5 (green), 0.5-0.8 (yellow), 0.8-1.0 (red)

### Panel 4: Malicious Trends
- **Type:** Time Series
- **Query:** `rate(xgb_predicted_malicious_total[5m])`

---

## Troubleshooting

### Issue: No anomaly files found
**Solution:** Run Stage 1 clustering first
```bash
python run_clustering.py
```

### Issue: Low recall (<0.70)
**Solution:** 
- Increase `n_estimators` to 600
- Adjust `scale_pos_weight`
- Check class balance

### Issue: Model overfitting
**Solution:**
- Decrease `max_depth` to 4
- Increase `subsample` to 0.9
- Add regularization

### Issue: Exporter shows 0 metrics
**Solution:**
- Verify anomaly cluster files exist
- Check model file path
- Review exporter logs

---

## Files

| File | Purpose |
|------|---------|
| `train_xgboost.py` | Train XGBoost model |
| `prometheus_exporter_xgboost.py` | Export metrics |
| `data/xgboost_threat_classifier.json` | Trained model |
| `data/xgboost_feature_names.pkl` | Feature list |
| `data/xgboost_metadata.json` | Model info |

---

## Complete Workflow

```bash
# Stage 1: Clustering
python run_clustering.py

# Stage 2: Train XGBoost
python train_xgboost.py

# Stage 2: Start Exporter
python prometheus_exporter_xgboost.py

# Verify metrics
curl http://localhost:8001/metrics
```

---

## Production Deployment

1. ✅ Run clustering on production data
2. ✅ Train XGBoost model
3. ✅ Start exporter as service
4. ✅ Configure Prometheus scraping
5. ✅ Import Grafana dashboard
6. ✅ Set up alerts for high-risk events

---

**Status:** Production Ready ✅  
**Version:** 2.0  
**Last Updated:** 2026-02-20
