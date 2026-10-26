"""
Phase 2: XGBoost-Based Threat Classification
Trains on all anomaly clusters from all hosts
"""

import pandas as pd
import numpy as np
import glob
import os
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import pickle

def load_anomaly_clusters(clusters_dir='data/clusters'):
    """Load all anomaly cluster files from anomaly folder"""
    
    print("=" * 70)
    print("LOADING ANOMALY CLUSTERS")
    print("=" * 70)
    
    anomaly_dir = os.path.join(clusters_dir, 'anomaly')
    anomaly_files = glob.glob(os.path.join(anomaly_dir, '*.csv'))
    
    if not anomaly_files:
        raise FileNotFoundError(f"No anomaly cluster files found in {anomaly_dir}")
    
    print(f"[FOUND] {len(anomaly_files)} anomaly cluster files")
    
    dfs = []
    for file in anomaly_files:
        df = pd.read_csv(file)
        host_name = os.path.basename(file).split('_cluster_')[0].replace('host_', '')
        df['source_host'] = host_name
        dfs.append(df)
        print(f"  - {os.path.basename(file)}: {len(df)} logs")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    
    print(f"\n[TOTAL] {len(combined_df)} anomaly logs from {len(anomaly_files)} hosts")
    
    return combined_df

def create_target_label(df):
    """Create broader detection target: sus=1 OR evil=1"""
    
    print("\n" + "=" * 70)
    print("TARGET LABEL CREATION")
    print("=" * 70)
    
    # Check if columns exist
    has_sus = 'sus' in df.columns
    has_evil = 'evil' in df.columns
    
    if not has_sus and not has_evil:
        print("[WARNING] No 'sus' or 'evil' columns found")
        print("[INFO] Creating synthetic labels (all anomalies = 1)")
        df['label'] = 1
    else:
        # Broader detection: sus=1 OR evil=1
        if has_sus and has_evil:
            df['label'] = ((df['sus'] == 1) | (df['evil'] == 1)).astype(int)
        elif has_sus:
            df['label'] = (df['sus'] == 1).astype(int)
        else:
            df['label'] = (df['evil'] == 1).astype(int)
    
    # Class distribution
    positive_count = (df['label'] == 1).sum()
    negative_count = (df['label'] == 0).sum()
    positive_pct = (positive_count / len(df)) * 100
    
    print(f"[LABEL] Positive class (suspicious/malicious): {positive_count} ({positive_pct:.1f}%)")
    print(f"[LABEL] Negative class (benign): {negative_count} ({100-positive_pct:.1f}%)")
    
    return df, positive_count, negative_count

def export_malicious_logs(df, clusters_dir='data/clusters'):
    """Export confirmed malicious logs (evil=1) to malicious folder"""
    
    print("\n" + "=" * 70)
    print("MALICIOUS LOGS EXPORT")
    print("=" * 70)
    
    malicious_dir = os.path.join(clusters_dir, 'malicious')
    os.makedirs(malicious_dir, exist_ok=True)
    
    if 'evil' in df.columns:
        malicious_df = df[df['evil'] == 1]
        
        if len(malicious_df) > 0:
            output_path = os.path.join(malicious_dir, 'malicious_logs.csv')
            malicious_df.to_csv(output_path, index=False)
            print(f"[MALICIOUS] {len(malicious_df)} confirmed evil logs exported")
            print(f"[MALICIOUS] Saved to: {output_path}")
        else:
            print("[MALICIOUS] No evil logs found")
    else:
        print("[MALICIOUS] No 'evil' column found, skipping export")

def preprocess_features(df):
    """Preprocess features for XGBoost"""
    
    print("\n" + "=" * 70)
    print("FEATURE PREPROCESSING")
    print("=" * 70)
    
    # Remove non-feature columns
    drop_cols = ['timestamp', 'sus', 'evil', 'label', 'source_host', 'cluster_label']
    drop_cols = [col for col in drop_cols if col in df.columns]
    
    X = df.drop(columns=drop_cols)
    y = df['label']
    
    print(f"[INITIAL] {X.shape[1]} features")
    
    # Keep only numeric columns
    numeric_cols = X.select_dtypes(include=[np.number]).columns
    X = X[numeric_cols]
    
    print(f"[NUMERIC] {X.shape[1]} numeric features")
    
    # Handle NaN values
    X = X.fillna(0)
    
    # Store feature names before conversion
    feature_names = X.columns.tolist()
    
    # Convert to float32 NumPy
    X = X.astype(np.float32).values
    y = y.values
    
    print(f"[FINAL] Shape: {X.shape}, dtype: {X.dtype}")
    
    return X, y, feature_names

def train_xgboost_model(X, y, positive_count, negative_count):
    """Train XGBoost classifier with optimal parameters"""
    
    print("\n" + "=" * 70)
    print("XGBOOST TRAINING")
    print("=" * 70)
    
    # Calculate scale_pos_weight
    scale_pos_weight = negative_count / positive_count
    print(f"[BALANCE] scale_pos_weight: {scale_pos_weight:.2f}")
    
    # Stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"[SPLIT] Train: {len(X_train)}, Test: {len(X_test)}")
    
    # XGBoost configuration
    model = XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        tree_method='hist',
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1
    )
    
    print("[TRAINING] XGBoost with 400 estimators...")
    
    # Train
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Evaluation
    print("\n" + "=" * 70)
    print("EVALUATION METRICS")
    print("=" * 70)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Malicious']))
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    
    roc_auc = roc_auc_score(y_test, y_proba)
    print(f"\nROC-AUC Score: {roc_auc:.4f}")
    
    # Risk tier analysis
    high_risk = (y_proba >= 0.8).sum()
    suspicious = ((y_proba >= 0.5) & (y_proba < 0.8)).sum()
    low_risk = (y_proba < 0.5).sum()
    
    print(f"\nRisk Tier Distribution:")
    print(f"  High Risk (≥0.8): {high_risk} ({high_risk/len(y_proba)*100:.1f}%)")
    print(f"  Suspicious (0.5-0.8): {suspicious} ({suspicious/len(y_proba)*100:.1f}%)")
    print(f"  Low Risk (<0.5): {low_risk} ({low_risk/len(y_proba)*100:.1f}%)")
    
    return model, X_test, y_test, y_proba

def save_model(model, feature_names):
    """Save trained model and metadata"""
    
    print("\n" + "=" * 70)
    print("SAVING MODEL")
    print("=" * 70)
    
    # Save model using XGBoost native format (faster, more stable)
    model_path = 'data/xgboost_threat_classifier.json'
    model.save_model(model_path)
    print(f"[SAVED] Model: {model_path}")
    
    # Save feature names
    features_path = 'data/xgboost_feature_names.pkl'
    with open(features_path, 'wb') as f:
        pickle.dump(feature_names, f)
    print(f"[SAVED] Features: {features_path}")
    
    # Save metadata
    metadata = {
        'model_type': 'XGBClassifier',
        'n_features': len(feature_names),
        'target': 'sus OR evil',
        'risk_tiers': {
            'high': '≥0.8',
            'suspicious': '0.5-0.8',
            'low': '<0.5'
        }
    }
    
    import json
    metadata_path = 'data/xgboost_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[SAVED] Metadata: {metadata_path}")

def main():
    """Main Phase 2 training pipeline"""
    
    print("=" * 70)
    print("PHASE 2: XGBOOST THREAT CLASSIFICATION")
    print("=" * 70)
    
    # Step 1: Load anomaly clusters
    df = load_anomaly_clusters()
    
    # Step 2: Create target label
    df, positive_count, negative_count = create_target_label(df)
    
    # Step 2.5: Export malicious logs
    export_malicious_logs(df)
    
    # Step 3: Preprocess features
    X, y, feature_names = preprocess_features(df)
    
    # Step 4: Train XGBoost
    model, X_test, y_test, y_proba = train_xgboost_model(X, y, positive_count, negative_count)
    
    # Step 5: Save model
    save_model(model, feature_names)
    
    print("\n" + "=" * 70)
    print("PHASE 2 TRAINING COMPLETE")
    print("=" * 70)
    print("✅ XGBoost model trained on all anomaly clusters")
    print("✅ Model saved to: data/xgboost_threat_classifier.json")
    print("✅ Ready for Prometheus export")
    print("=" * 70)

if __name__ == "__main__":
    main()
