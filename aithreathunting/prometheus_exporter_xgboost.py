"""
Phase 2: Prometheus Exporter for XGBoost Threat Classification
Exposes real-time metrics for monitoring
"""

import time
import pickle
import pandas as pd
import numpy as np
import glob
import os
from xgboost import XGBClassifier
from prometheus_client import start_http_server, Gauge, Counter

class XGBoostThreatExporter:
    """Prometheus exporter for XGBoost threat classification"""
    
    def __init__(self, model_path='data/xgboost_threat_classifier.json',
                 features_path='data/xgboost_feature_names.pkl',
                 clusters_dir='data/clusters'):
        
        self.clusters_dir = clusters_dir
        
        # Load model using XGBoost native format (faster, more stable)
        print("[LOADING] XGBoost model...")
        self.model = XGBClassifier()
        self.model.load_model(model_path)
        
        # Load feature names
        with open(features_path, 'rb') as f:
            self.feature_names = pickle.load(f)
        
        print(f"[LOADED] Model with {len(self.feature_names)} features")
        
        # Initialize previous values for delta calculation
        self.prev_anomaly_count = 0
        self.prev_malicious = 0
        self.prev_benign = 0
        self.prev_high_risk = 0
        self.prev_suspicious = 0
        
        # Initialize Prometheus metrics
        
        # Counters for event tracking (incremental)
        self.xgb_anomaly_events_total = Counter(
            'xgb_anomaly_events_total',
            'Total anomaly (-1 cluster) events detected over time'
        )
        
        self.xgb_malicious_events_total = Counter(
            'xgb_malicious_events_total',
            'Total malicious events detected over time'
        )
        
        self.xgb_benign_events_total = Counter(
            'xgb_benign_events_total',
            'Total benign events detected over time'
        )
        
        self.xgb_high_risk_events_total = Counter(
            'xgb_high_risk_events_total',
            'Total high-risk events (probability >= 0.8) over time'
        )
        
        self.xgb_suspicious_events_total = Counter(
            'xgb_suspicious_events_total',
            'Total suspicious events (probability 0.5-0.8) over time'
        )
        
        # Gauges for snapshot values (current state)
        self.xgb_anomaly_total = Gauge(
            'xgb_anomaly_total',
            'Current total logs in dataset (system-wide)'
        )
        
        self.xgb_predicted_malicious_total = Gauge(
            'xgb_predicted_malicious_total',
            'Current predicted malicious count'
        )
        
        self.xgb_predicted_benign_total = Gauge(
            'xgb_predicted_benign_total',
            'Current predicted benign count'
        )
        
        self.xgb_high_risk_total = Gauge(
            'xgb_high_risk_total',
            'Current high-risk event count (probability >= 0.8)'
        )
        
        self.xgb_suspicious_total = Gauge(
            'xgb_suspicious_total',
            'Current suspicious event count (probability 0.5-0.8)'
        )
        
        self.xgb_avg_probability = Gauge(
            'xgb_avg_probability',
            'Average risk probability (0-1 scale)'
        )
        
        self.xgb_malicious_rate = Gauge(
            'xgb_malicious_rate',
            'Malicious rate as percentage (0-100)'
        )
        
        self.anomaly_rate = Gauge(
            'anomaly_rate',
            'Percentage of anomaly logs across entire dataset'
        )
        
        # Cluster distribution metrics
        self.cluster_normal_total = Gauge(
            'cluster_normal_total',
            'Total logs in normal clusters'
        )
        
        self.cluster_anomaly_total = Gauge(
            'cluster_anomaly_total',
            'Total logs in anomaly (-1) cluster'
        )
        
        self.malicious_logs_total = Gauge(
            'malicious_logs_total',
            'Total number of malicious logs from malicious folder'
        )
        
        self.total_logs_count = Gauge(
            'total_logs_count',
            'Total number of logs across all clusters'
        )
        
        self.normal_cluster_count = Gauge(
            'normal_cluster_count',
            'Number of normal clusters'
        )
        
        self.anomaly_cluster_count = Gauge(
            'anomaly_cluster_count',
            'Number of anomaly (-1) clusters'
        )
        
        self.malicious_rate_system = Gauge(
            'malicious_rate_system',
            'Malicious percentage across entire dataset'
        )
        
        print("[METRICS] Prometheus metrics initialized")
    
    def load_all_cluster_data(self):
        """Load ALL cluster files (normal + anomaly + malicious) for system-wide analysis"""
        
        normal_dir = os.path.join(self.clusters_dir, 'normal')
        anomaly_dir = os.path.join(self.clusters_dir, 'anomaly')
        malicious_dir = os.path.join(self.clusters_dir, 'malicious')
        
        normal_files = glob.glob(os.path.join(normal_dir, '*.csv'))
        anomaly_files = glob.glob(os.path.join(anomaly_dir, '*.csv'))
        malicious_files = glob.glob(os.path.join(malicious_dir, '*.csv'))
        
        if not normal_files and not anomaly_files and not malicious_files:
            print(f"[WARNING] No cluster files found in {self.clusters_dir}")
            return None, [], [], []
        
        dfs = []
        for file in normal_files + anomaly_files + malicious_files:
            df = pd.read_csv(file)
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True) if dfs else None
        
        return combined_df, normal_files, anomaly_files, malicious_files
    
    def calculate_cluster_distribution(self):
        """Calculate normal vs anomaly vs malicious cluster distribution"""
        
        normal_dir = os.path.join(self.clusters_dir, 'normal')
        anomaly_dir = os.path.join(self.clusters_dir, 'anomaly')
        malicious_dir = os.path.join(self.clusters_dir, 'malicious')
        
        normal_files = glob.glob(os.path.join(normal_dir, '*.csv'))
        anomaly_files = glob.glob(os.path.join(anomaly_dir, '*.csv'))
        malicious_files = glob.glob(os.path.join(malicious_dir, '*.csv'))
        
        normal_count = 0
        anomaly_count = 0
        malicious_count = 0
        
        for file in normal_files:
            df = pd.read_csv(file)
            normal_count += len(df)
        
        for file in anomaly_files:
            df = pd.read_csv(file)
            anomaly_count += len(df)
        
        for file in malicious_files:
            df = pd.read_csv(file)
            malicious_count += len(df)
        
        return normal_count, anomaly_count, malicious_count
    
    def preprocess_for_prediction(self, df):
        """Preprocess data for XGBoost prediction"""
        
        # Remove non-feature columns
        drop_cols = ['timestamp', 'sus', 'evil', 'label', 'source_host', 'cluster_label']
        drop_cols = [col for col in drop_cols if col in df.columns]
        
        X = df.drop(columns=drop_cols, errors='ignore')
        
        # Keep only numeric
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X = X[numeric_cols]
        
        # Align with training features
        missing_cols = set(self.feature_names) - set(X.columns)
        for col in missing_cols:
            X[col] = 0
        
        X = X[self.feature_names]
        
        # Fill NaN and convert to float32
        X = X.fillna(0).astype(np.float32)
        
        return X
    
    def predict_and_update_metrics(self):
        """Load data, predict, and update Prometheus metrics"""
        
        try:
            # Calculate cluster distribution (Stage 1 metrics)
            normal_count, anomaly_count, malicious_count = self.calculate_cluster_distribution()
            
            self.cluster_normal_total.set(normal_count)
            self.cluster_anomaly_total.set(anomaly_count)
            self.malicious_logs_total.set(malicious_count)
            
            # Calculate system-wide rates (malicious is subset of anomaly, don't double count)
            total_logs = normal_count + anomaly_count
            anomaly_rate = (anomaly_count / total_logs) * 100 if total_logs > 0 else 0
            malicious_rate_system = (malicious_count / total_logs) * 100 if total_logs > 0 else 0
            self.anomaly_rate.set(anomaly_rate)
            self.malicious_rate_system.set(malicious_rate_system)
            
            print(f"[CLUSTER] Normal logs: {normal_count}")
            print(f"[CLUSTER] Anomaly logs: {anomaly_count}")
            print(f"[CLUSTER] Malicious logs: {malicious_count}")
            
            # Load ALL cluster data for system-wide XGBoost prediction
            df, normal_files, anomaly_files, malicious_files = self.load_all_cluster_data()
            
            if df is None or len(df) == 0:
                print("[INFO] No cluster data to process")
                return
            
            # Total logs and cluster counts
            total_logs_count = len(df)
            self.total_logs_count.set(total_logs_count)
            self.normal_cluster_count.set(len(normal_files))
            self.anomaly_cluster_count.set(len(anomaly_files))
            
            # Preprocess
            X = self.preprocess_for_prediction(df)
            
            # Predict
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]
            
            # Calculate metrics (system-wide)
            predicted_malicious = int((predictions == 1).sum())
            predicted_benign = int((predictions == 0).sum())
            high_risk = int((probabilities >= 0.8).sum())
            suspicious = int(((probabilities >= 0.5) & (probabilities < 0.8)).sum())
            avg_probability = float(probabilities.mean())
            
            # Calculate rates (percentages across entire system)
            malicious_rate = (predicted_malicious / total_logs * 100) if total_logs > 0 else 0
            
            # Calculate deltas (only increment new events)
            delta_anomaly = anomaly_count - self.prev_anomaly_count
            delta_malicious = predicted_malicious - self.prev_malicious
            delta_benign = predicted_benign - self.prev_benign
            delta_high_risk = high_risk - self.prev_high_risk
            delta_suspicious = suspicious - self.prev_suspicious
            
            # Update Counters (only increment if positive delta)
            if delta_anomaly > 0:
                self.xgb_anomaly_events_total.inc(delta_anomaly)
            if delta_malicious > 0:
                self.xgb_malicious_events_total.inc(delta_malicious)
            if delta_benign > 0:
                self.xgb_benign_events_total.inc(delta_benign)
            if delta_high_risk > 0:
                self.xgb_high_risk_events_total.inc(delta_high_risk)
            if delta_suspicious > 0:
                self.xgb_suspicious_events_total.inc(delta_suspicious)
            
            # Update previous values
            self.prev_anomaly_count = anomaly_count
            self.prev_malicious = predicted_malicious
            self.prev_benign = predicted_benign
            self.prev_high_risk = high_risk
            self.prev_suspicious = suspicious
            
            # Update Gauges (snapshot values)
            self.xgb_anomaly_total.set(total_logs)
            self.xgb_predicted_malicious_total.set(predicted_malicious)
            self.xgb_predicted_benign_total.set(predicted_benign)
            self.xgb_high_risk_total.set(high_risk)
            self.xgb_suspicious_total.set(suspicious)
            self.xgb_avg_probability.set(avg_probability)
            self.xgb_malicious_rate.set(malicious_rate)
            
            # Log metrics
            print("DEBUG → Total logs:", total_logs)
            print("DEBUG → Predicted malicious:", predicted_malicious)
            print("DEBUG → Malicious %:", malicious_rate)
            print("DEBUG → Anomaly %:", anomaly_rate)
            print("DEBUG → Malicious system %:", malicious_rate_system)
            print("DEBUG → Cluster normal:", normal_count)
            print("DEBUG → Cluster anomaly:", anomaly_count)
            print("DEBUG → Cluster malicious:", malicious_count)
            print(f"[XGBOOST] Total logs processed: {total_logs}")
            print(f"[XGBOOST] Predicted malicious: {predicted_malicious} ({malicious_rate:.2f}% of system)")
            print(f"[XGBOOST] Predicted benign: {predicted_benign}")
            print(f"[XGBOOST] High risk: {high_risk}")
            print(f"[XGBOOST] Suspicious: {suspicious}")
            print(f"[XGBOOST] System-wide avg probability: {avg_probability:.3f}")
            if delta_anomaly > 0:
                print(f"[DELTA] New anomaly events: +{delta_anomaly}")
            if delta_malicious > 0:
                print(f"[DELTA] New malicious events: +{delta_malicious}")
            if delta_high_risk > 0:
                print(f"[DELTA] New high-risk events: +{delta_high_risk}")
            
        except Exception as e:
            print(f"[ERROR] {e}")
    
    def run(self, update_interval=15):
        """Run exporter with periodic updates"""
        
        print("=" * 70)
        print("PHASE 2: XGBOOST PROMETHEUS EXPORTER")
        print("=" * 70)
        print(f"Endpoint: http://localhost:8001/metrics")
        print(f"Update interval: {update_interval} seconds")
        print("\nMetrics exported:")
        print("  Stage 1 (Clustering):")
        print("    - cluster_normal_total (Gauge)")
        print("    - cluster_anomaly_total (Gauge)")
        print("    - malicious_logs_total (Gauge)")
        print("    - anomaly_rate (Gauge)")
        print("    - malicious_rate_system (Gauge)")
        print("    - total_logs_count (Gauge)")
        print("    - normal_cluster_count (Gauge)")
        print("    - anomaly_cluster_count (Gauge)")
        print("  Stage 2 (XGBoost):")
        print("    Counters (for time-series/spikes):")
        print("      - xgb_anomaly_events_total")
        print("      - xgb_malicious_events_total")
        print("      - xgb_benign_events_total")
        print("      - xgb_high_risk_events_total")
        print("      - xgb_suspicious_events_total")
        print("    Gauges (for snapshots):")
        print("      - xgb_anomaly_total")
        print("      - xgb_predicted_malicious_total")
        print("      - xgb_predicted_benign_total")
        print("      - xgb_high_risk_total")
        print("      - xgb_suspicious_total")
        print("      - xgb_avg_probability")
        print("      - xgb_malicious_rate")
        print("=" * 70)
        print("\nStarting metric updates...\n")
        
        while True:
            self.predict_and_update_metrics()
            time.sleep(update_interval)

def main():
    """Main exporter entry point"""
    
    # Initialize exporter
    exporter = XGBoostThreatExporter()

    # Start HTTP server
    start_http_server(8001)

    # Note: the time-series line-graph panels in the Grafana dashboard are fed by a
    # separate, clearly-labeled synthetic data generator (demo/demo_timeseries.py).
    # It is intentionally NOT started here, so this exporter only ever reports metrics
    # computed from real model predictions on real cluster files.

    # Run exporter
    exporter.run(update_interval=15)


if __name__ == "__main__":
    main()
