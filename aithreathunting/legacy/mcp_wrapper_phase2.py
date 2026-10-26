import os
import pickle
import pandas as pd
import json
import numpy as np
from sklearn.ensemble import IsolationForest

class MCPModelWrapper:
    def __init__(self, config_path="data/config.json"):
        with open(config_path) as f:
            config = json.load(f)
        
        self.mode = config.get("mode", "unsupervised")
        self.threshold_risk = config.get("threshold_risk", 0.7)
        self.rf_model = None
        self.label_encoders = None
        
        # Load Random Forest for Stage 2 classification
        if self.mode in ["supervised", "hybrid"]:
            model_path = config.get("model_path", "data/rf_event_classifier.pkl")
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    self.rf_model = pickle.load(f)
                print(f"[MCP] Loaded RF model: {model_path}")
                
                encoders_path = config.get("encoders_path", "data/label_encoders.pkl")
                if os.path.exists(encoders_path):
                    with open(encoders_path, "rb") as f:
                        self.label_encoders = pickle.load(f)
        
        # Stage B: Anomaly modeling
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42, n_jobs=-1)
        self.anomaly_model_trained = False
        self.threat_stats = {"attack": 0, "system_noise": 0}

    def analyze_cluster_distribution(self, cluster_dir="data/clusters"):
        """Count cluster distribution from HDBSCAN output"""
        cluster_counts = {}
        
        if not os.path.exists(cluster_dir):
            return cluster_counts
        
        for file in os.listdir(cluster_dir):
            if file.endswith('.csv'):
                if 'anomaly' in file:
                    cluster_id = -1
                else:
                    cluster_id = int(file.split('_cluster_')[1].replace('.csv', ''))
                
                df = pd.read_csv(os.path.join(cluster_dir, file))
                cluster_counts[cluster_id] = len(df)
        
        return cluster_counts

    def classify_anomalies(self, anomaly_csv="data/clusters/host_*_cluster_anomaly.csv"):
        """Stage 2: Run Random Forest on cluster -1 to classify threats"""
        import glob
        
        if self.rf_model is None:
            print("[MCP Stage 2] No RF model loaded, skipping classification")
            return {"attack": 0, "system_noise": 0}
        
        anomaly_files = glob.glob(anomaly_csv)
        if not anomaly_files:
            return {"attack": 0, "system_noise": 0}
        
        dfs = [pd.read_csv(f) for f in anomaly_files]
        anomaly_df = pd.concat(dfs, ignore_index=True)
        
        # Prepare features for RF (match training format)
        try:
            # Get numeric features
            numeric_cols = anomaly_df.select_dtypes(include=['int64', 'float64']).columns
            X = anomaly_df[numeric_cols].fillna(0)
            
            # Run RF prediction
            predictions = self.rf_model.predict_proba(X)
            
            # If prob > threshold_risk, flag as ATTACK
            attack_count = np.sum(predictions[:, 1] > self.threshold_risk)
            system_noise_count = len(predictions) - attack_count
            
            self.threat_stats = {
                "attack": int(attack_count),
                "system_noise": int(system_noise_count)
            }
            
            print(f"[MCP Stage 2] Classified: {attack_count} attacks, {system_noise_count} system noise")
            
        except Exception as e:
            print(f"[MCP Stage 2] Classification error: {e}")
            self.threat_stats = {"attack": 0, "system_noise": 0}
        
        return self.threat_stats

    def train_anomaly_model(self, anomaly_csv="data/clusters/host_*_cluster_anomaly.csv"):
        """Train Isolation Forest on anomaly cluster"""
        import glob
        
        anomaly_files = glob.glob(anomaly_csv)
        if not anomaly_files:
            return False
        
        dfs = [pd.read_csv(f) for f in anomaly_files]
        anomaly_df = pd.concat(dfs, ignore_index=True)
        
        # Select numeric features
        numeric_cols = anomaly_df.select_dtypes(include=['int64', 'float64']).columns
        X = anomaly_df[numeric_cols].fillna(0)
        
        self.isolation_forest.fit(X)
        self.anomaly_model_trained = True
        print(f"[MCP Stage B] Trained on {len(anomaly_df)} anomalies")
        return True

    def calculate_risk_score(self, anomaly_csv="data/clusters/host_*_cluster_anomaly.csv"):
        """Calculate average risk score for anomalies"""
        import glob
        
        if not self.anomaly_model_trained:
            self.train_anomaly_model(anomaly_csv)
        
        anomaly_files = glob.glob(anomaly_csv)
        if not anomaly_files:
            return 0.0
        
        dfs = [pd.read_csv(f) for f in anomaly_files]
        anomaly_df = pd.concat(dfs, ignore_index=True)
        
        numeric_cols = anomaly_df.select_dtypes(include=['int64', 'float64']).columns
        X = anomaly_df[numeric_cols].fillna(0)
        
        # Get anomaly scores (lower = more anomalous)
        scores = self.isolation_forest.score_samples(X)
        # Normalize to 0-1 (higher = more risky)
        risk_score = 1 - ((scores - scores.min()) / (scores.max() - scores.min() + 1e-10))
        
        return float(risk_score.mean())
