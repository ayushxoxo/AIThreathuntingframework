# 📊 Grafana Dashboard Import Guide

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🟥 ROW 1: THREAT OVERVIEW (Big Numbers)                        │
├──────────┬──────────┬──────────┬──────────────────────────────┤
│ Total    │ Predicted│ High Risk│ Average Risk                 │
│ Anomalies│ Malicious│ Events   │ Probability                  │
│ (Blue)   │ (Thresh) │ (Red)    │ (Percent)                    │
└──────────┴──────────┴──────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  🟨 ROW 2: THREAT RATIO VISUALIZATION                           │
├──────────────────────────────┬──────────────────────────────────┤
│ Benign vs Malicious          │ Attack Probability Health        │
│ (Pie Chart)                  │ (Gauge: Green/Yellow/Red)        │
│ Green: Benign                │ 0-0.3: Green                     │
│ Red: Malicious               │ 0.3-0.6: Yellow                  │
│                              │ 0.6-1.0: Red                     │
└──────────────────────────────┴──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  🟦 ROW 3: TIME-SERIES MONITORING                               │
├──────────────────────────────┬──────────────────────────────────┤
│ Malicious Events Over Time   │ High Risk Events Over Time       │
│ (Line Graph)                 │ (Attack Spike Detector)          │
│ Shows trend                  │ ⚠️ Alert if >5 events            │
└──────────────────────────────┴──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  🟩 ROW 4: RISK TIER BREAKDOWN                                  │
├──────────┬──────────┬──────────────────────────────────────────┤
│ High Risk│Suspicious│ Benign                                   │
│ (≥0.8)   │(0.5-0.8) │ (<0.5)                                   │
│ Dark Red │ Yellow   │ Green                                    │
└──────────┴──────────┴──────────────────────────────────────────┘
```

---

## Import Steps

### 1. Start Services

```bash
# Start XGBoost exporter
python prometheus_exporter_xgboost.py

# Start Prometheus (if not running)
cd ..\prometheus-3.9.1.windows-amd64\prometheus-3.9.1.windows-amd64
prometheus.exe --config.file=prometheus.yml

# Start Grafana (if not running)
cd ..\..\grafana-enterprise_12.3.3_21957728731_windows_amd64\grafana-12.3.3\bin
grafana-server.exe
```

### 2. Configure Prometheus

Edit `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: "xgboost_exporter"
    scrape_interval: 10s
    static_configs:
      - targets: ["127.0.0.1:8001"]
```

### 3. Import Dashboard

1. Open Grafana: http://localhost:3000
2. Login: admin/admin
3. Click **+** → **Import**
4. Click **Upload JSON file**
5. Select: `monitoring/grafana_dashboard_xgboost.json`
6. Select Prometheus data source
7. Click **Import**

---

## Panel Details

### 🟥 Row 1: Threat Overview

#### Panel 1: Total Anomaly Logs
- **Metric:** `xgb_anomaly_total`
- **Color:** Blue background
- **Purpose:** Total anomalies processed

#### Panel 2: Predicted Malicious ⭐
- **Metric:** `xgb_predicted_malicious_total`
- **Thresholds:**
  - Green: 0-100
  - Yellow: 100-500
  - Red: >500
- **Purpose:** Main threat indicator

#### Panel 3: High Risk Events ⚠️
- **Metric:** `xgb_high_risk_total`
- **Color:** Red if >0
- **Purpose:** Critical threats (probability ≥0.8)

#### Panel 4: Average Risk Probability
- **Metric:** `xgb_avg_probability * 100`
- **Unit:** Percent
- **Thresholds:**
  - Green: 0-30%
  - Yellow: 30-60%
  - Red: >60%

---

### 🟨 Row 2: Threat Ratio

#### Panel 5: Benign vs Malicious (Pie Chart)
- **Metrics:**
  - `xgb_predicted_benign_total` (Green)
  - `xgb_predicted_malicious_total` (Red)
- **Purpose:** Distribution view

#### Panel 6: Attack Probability Health (Gauge)
- **Metric:** `xgb_avg_probability`
- **Range:** 0-1
- **Colors:**
  - Green: <0.3
  - Yellow: 0.3-0.6
  - Red: >0.6
- **Purpose:** Overall system health

---

### 🟦 Row 3: Time-Series

#### Panel 7: Malicious Events Over Time
- **Metric:** `xgb_predicted_malicious_total`
- **Type:** Line graph
- **Purpose:** Trend detection

#### Panel 8: High Risk Events Over Time ⚠️
- **Metric:** `xgb_high_risk_total`
- **Type:** Line graph with alert
- **Alert:** Triggers if >5 high-risk events
- **Purpose:** Attack spike detector

---

### 🟩 Row 4: Risk Tier Breakdown

#### Panel 9: High Risk
- **Metric:** `xgb_high_risk_total`
- **Color:** Dark Red
- **Label:** ≥0.8

#### Panel 10: Suspicious
- **Metric:** `xgb_suspicious_total`
- **Color:** Yellow
- **Label:** 0.5-0.8

#### Panel 11: Benign
- **Metric:** `xgb_predicted_benign_total`
- **Color:** Green
- **Label:** <0.5

---

## Alerts Configured

### High Risk Spike Alert
- **Condition:** `xgb_high_risk_total > 5`
- **Frequency:** Check every 1 minute
- **Message:** "High risk events detected! Immediate investigation required."
- **Action:** Configure notification channels in Grafana

---

## Metrics Reference

| Metric | Description | Type |
|--------|-------------|------|
| `xgb_anomaly_total` | Total anomaly logs | Gauge |
| `xgb_predicted_malicious_total` | Malicious count | Gauge |
| `xgb_predicted_benign_total` | Benign count | Gauge |
| `xgb_high_risk_total` | High risk (≥0.8) | Gauge |
| `xgb_suspicious_total` | Suspicious (0.5-0.8) | Gauge |
| `xgb_avg_probability` | Average risk score | Gauge |

---

## Dashboard Settings

- **Refresh:** Every 10 seconds
- **Time Range:** Last 1 hour
- **Timezone:** Browser
- **Auto-refresh:** Enabled

---

## Customization

### Change Thresholds

Edit panel → Field → Thresholds:
```
Green: 0
Yellow: 100
Red: 500
```

### Change Colors

Edit panel → Field → Color scheme

### Add Notifications

1. Alerting → Notification channels
2. Add Slack/Email/PagerDuty
3. Link to High Risk Spike Alert

---

## Troubleshooting

### No Data Showing
1. Check exporter: http://localhost:8001/metrics
2. Check Prometheus: http://localhost:9090/targets
3. Verify data source in Grafana
4. Wait 10-20 seconds for first scrape

### Metrics Not Found
1. Ensure exporter is running
2. Check Prometheus scrape config
3. Verify metric names match exactly

### Alert Not Triggering
1. Go to panel → Alert tab
2. Check condition
3. Test alert
4. Configure notification channel

---

## Production Checklist

- ✅ Exporter running on port 8001
- ✅ Prometheus scraping every 10s
- ✅ Grafana dashboard imported
- ✅ All panels showing data
- ✅ Alerts configured
- ✅ Notification channels set up

---

**Dashboard File:** `monitoring/grafana_dashboard_xgboost.json`  
**Status:** Production Ready ✅  
**Last Updated:** 2026-02-20
