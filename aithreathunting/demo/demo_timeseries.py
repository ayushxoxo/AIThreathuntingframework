"""
demo_timeseries.py

** DEMO / PLACEHOLDER ONLY — THIS SCRIPT DOES NOT PRODUCE REAL DETECTION DATA. **

Every value this script exports is generated with random.randint(). It exists
purely to put a moving line on the Grafana "time-series" panels during a live
demo, before enough real scrape intervals have accumulated to draw a trend
from the actual exporter (prometheus_exporter_xgboost.py).

It is intentionally NOT imported or started by prometheus_exporter_xgboost.py.
Run it manually, on its own port, only if you specifically want a cosmetic
moving-line panel for a demo — never present its output as measured model
behavior, and do not scrape it into the same dashboard rows as the real
cluster_* / xgb_* metrics without labeling the panel as synthetic.

Metrics published (all synthetic):
1. Normal cluster activity   (random int 80-100)
2. Anomaly cluster activity  (random int 60-90)
3. High-priority anomaly events (random int 40-80)
"""

import time
import random
from prometheus_client import start_http_server, Gauge


# -------------------------------
# Metric Definition
# -------------------------------

cluster_trend = Gauge(
    'cluster_activity_trend',
    'Cluster activity timeline for visualization',
    ['type']
)


# -------------------------------
# Update Function
# -------------------------------

def update_metrics():

    # Simulated values (visual purposes)
    normal_value = random.randint(80, 100)
    anomaly_value = random.randint(60, 90)
    high_priority_value = random.randint(40, 80)

    # Update Prometheus metrics
    cluster_trend.labels(type="Normal_Clusters").set(normal_value)
    cluster_trend.labels(type="Anomaly_Clusters").set(anomaly_value)
    cluster_trend.labels(type="High_Priority_Anomaly").set(high_priority_value)

    print("Updated metrics:")
    print("Normal:", normal_value)
    print("Anomaly:", anomaly_value)
    print("High Priority:", high_priority_value)
    print("---------------------------------")


# -------------------------------
# Main Loop
# -------------------------------

def main():

    print("=" * 60)
    print("DEMO TIME-SERIES EXPORTER — SYNTHETIC DATA, NOT REAL DETECTIONS")
    print("=" * 60)

    print("Prometheus metrics available at:")
    print("http://localhost:9000/metrics")
    print()

    # Start Prometheus endpoint
    start_http_server(9000)

    while True:
        update_metrics()
        time.sleep(5)


# -------------------------------
# Entry Point
# -------------------------------

if __name__ == "__main__":
    main()