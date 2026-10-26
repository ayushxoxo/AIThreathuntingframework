import pandas as pd
import glob
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

print("=" * 70)
print("Training Random Forest on Anomaly Cluster Data")
print("=" * 70)

# Check if clustering has been run
cluster_dir = "data/clusters"
if not os.path.exists(cluster_dir):
    print("\n[ERROR] Clustering not run yet!")
    print("Please run: python run_phase1.py first")
    exit(1)

# Load all anomaly cluster files (cluster -1)
anomaly_files = glob.glob(f"{cluster_dir}/*_cluster_anomaly.csv")

if not anomaly_files:
    print("\n[ERROR] No anomaly cluster files found!")
    print("Please run: python run_phase1.py first")
    exit(1)

print(f"\n[LOADING] Found {len(anomaly_files)} anomaly cluster files")

# Concatenate all anomaly data
dfs = []
for file in anomaly_files:
    df = pd.read_csv(file)
    dfs.append(df)
    print(f"[LOADED] {file}: {len(df)} rows")

anomaly_df = pd.concat(dfs, ignore_index=True)
print(f"\n[TOTAL] {len(anomaly_df)} anomaly records")

# Check if target column exists
if 'sus' not in anomaly_df.columns and 'evil' not in anomaly_df.columns:
    print("\n[WARNING] No 'sus' or 'evil' label column found")
    print("[INFO] Creating synthetic labels based on cluster_label")
    # Use cluster_label as proxy (all -1 are anomalies, label as 1)
    anomaly_df['sus'] = 1

# Define target
if 'sus' in anomaly_df.columns:
    y = anomaly_df['sus']
elif 'evil' in anomaly_df.columns:
    y = anomaly_df['evil']
else:
    print("[ERROR] No target column available")
    exit(1)

print(f"\n[TARGET] Using '{y.name}' as target variable")
print(f"[DISTRIBUTION] Class 0: {(y==0).sum()}, Class 1: {(y==1).sum()}")

# Drop non-feature columns
drop_cols = ['timestamp', 'args', 'parsed_args', 'arg_names', 'stackAddresses', 
             'cluster_label', 'sus', 'evil']
X = anomaly_df.drop(columns=[col for col in drop_cols if col in anomaly_df.columns], errors='ignore')

# Encode categorical features
label_encoders = {}
categorical_cols = X.select_dtypes(include=['object']).columns

print(f"\n[ENCODING] Processing {len(categorical_cols)} categorical columns")
for col in categorical_cols:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    label_encoders[col] = le
    print(f"  - {col}: {len(le.classes_)} unique values")

# Fill missing values
X = X.fillna(0)

print(f"\n[FEATURES] Final feature matrix: {X.shape}")
print(f"[FEATURES] Columns: {list(X.columns[:10])}...")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"\n[SPLIT] Train: {len(X_train)}, Test: {len(X_test)}")

# Train Random Forest
print("\n[TRAINING] Random Forest Classifier...")
model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1, max_depth=10)
model.fit(X_train, y_train)

# Evaluate
train_score = model.score(X_train, y_train)
test_score = model.score(X_test, y_test)

print(f"[ACCURACY] Train: {train_score:.3f}, Test: {test_score:.3f}")

# Save model
model_path = "data/rf_event_classifier.pkl"
with open(model_path, "wb") as f:
    pickle.dump(model, f)
print(f"\n[SAVED] Model: {model_path}")

# Save encoders
encoders_path = "data/label_encoders.pkl"
with open(encoders_path, "wb") as f:
    pickle.dump(label_encoders, f)
print(f"[SAVED] Encoders: {encoders_path}")

# Save feature names for reference
feature_names_path = "data/feature_names.pkl"
with open(feature_names_path, "wb") as f:
    pickle.dump(list(X.columns), f)
print(f"[SAVED] Feature names: {feature_names_path}")

print("\n" + "=" * 70)
print("Random Forest Training Complete!")
print("=" * 70)
print(f"Model trained on {len(anomaly_df)} anomaly records")
print(f"Ready for Stage 2 classification")
print("=" * 70)
