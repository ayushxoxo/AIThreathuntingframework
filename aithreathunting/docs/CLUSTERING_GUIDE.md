# 🚀 Production-Ready HDBSCAN Clustering Pipeline

## Overview
Complete, configurable, and scalable clustering pipeline for log anomaly detection.

---

## Quick Start

### 1. Run with Default Configuration
```bash
python run_clustering.py
```

### 2. Run All Experiments (4 Configurations)
```bash
python -c "from experiments import ExperimentRunner; runner = ExperimentRunner('data/merged_output1.csv'); runner.run_all_experiments()"
```

---

## Architecture

```
Raw Logs
    ↓
[Preprocessing]
  - Drop constant/high-null columns
  - Encode categorical (label/frequency)
  - Remove correlated features
  - StandardScaler (mandatory)
  - Convert to float32
    ↓
[Dimensionality Reduction]
  Mode A: PCA (95% variance)
  Mode B: UMAP (10 dimensions)
  Mode C: None (scaled only)
    ↓
[HDBSCAN Clustering]
  - Dynamic min_cluster_size (1-3% of data)
  - Configurable min_samples (10, 20, 50)
  - Multiple metrics (euclidean, manhattan, cosine)
    ↓
[Results]
  - Normal logs → Stable clusters
  - Attack logs → Label -1 (anomaly)
  - Small/unstable clusters → Anomaly candidates
```

---

## Configuration File

Edit `clustering_config.json`:

```json
{
  "data": {
    "csv_path": "data/merged_output1.csv",
    "output_dir": "data/clusters"
  },
  "preprocessing": {
    "null_threshold": 0.5,
    "correlation_threshold": 0.9,
    "high_cardinality_threshold": 100
  },
  "dimensionality_reduction": {
    "mode": "pca",
    "pca_variance": 0.95
  },
  "clustering": {
    "min_cluster_size_pct": 0.02,
    "min_samples": 20,
    "metric": "euclidean"
  }
}
```

---

## Experimental Configurations

### Config 1: PCA + Euclidean (Default)
- Best for: General purpose
- Speed: Fast
- Memory: Low

### Config 2: PCA + Manhattan
- Best for: High-dimensional sparse data
- Speed: Fast
- Memory: Low

### Config 3: UMAP + Euclidean
- Best for: Complex non-linear patterns
- Speed: Slower
- Memory: Medium
- Requires: `pip install umap-learn`

### Config 4: Scaled Only + Euclidean
- Best for: Low-dimensional data
- Speed: Fastest
- Memory: Lowest

---

## Parameter Tuning Guide

### min_cluster_size_pct
- **0.01 (1%)**: More clusters, fewer anomalies
- **0.02 (2%)**: Balanced (recommended)
- **0.03 (3%)**: Fewer clusters, more anomalies

### min_samples
- **10**: Loose density, more clusters
- **20**: Balanced (recommended)
- **50**: Strict density, fewer clusters

### metric
- **euclidean**: General purpose (default)
- **manhattan**: Sparse/high-dimensional data
- **cosine**: Text/frequency features

### pca_variance
- **0.90**: Faster, less accurate
- **0.95**: Balanced (recommended)
- **0.99**: Slower, more accurate

---

## Expected Results

### Good Configuration
- **Anomaly rate**: 5-20%
- **Clusters**: 10-100 stable clusters
- **Largest cluster**: 30-60% of data

### Too Strict (Anomaly rate > 25%)
- Increase `min_cluster_size_pct`
- Decrease `min_samples`
- Use PCA with lower variance

### Too Loose (Anomaly rate < 1%)
- Decrease `min_cluster_size_pct`
- Increase `min_samples`
- Use UMAP instead of PCA

---

## Output Files

### Cluster Files
- `data/clusters/normal/host_*_cluster_0.csv` - Normal cluster 0
- `data/clusters/normal/host_*_cluster_1.csv` - Normal cluster 1
- `data/clusters/anomaly/host_*_cluster_-1.csv` - Anomalies (-1)

### Summary Files
- `results/clustering_summary.json` - Configuration and results
- `results/experiment_results.csv` - Comparison of all experiments

---

## Evaluation

### Without Ground Truth
Metrics provided:
- Number of clusters
- Anomaly percentage
- Outlier score distribution
- Cluster stability metrics

### With Ground Truth
Set in config:
```json
{
  "evaluation": {
    "has_ground_truth": true,
    "ground_truth_column": "label"
  }
}
```

Metrics provided:
- Precision (anomaly class)
- Recall (attack detection)
- F1 Score
- Confusion Matrix

---

## Performance Optimization

### For Large Datasets (>100k rows)
1. Use PCA (not UMAP)
2. Set `pca_variance=0.90` (fewer components)
3. Increase `min_cluster_size_pct=0.03`
4. Use `metric='euclidean'`

### For Memory Constraints
1. Pipeline uses float32 automatically
2. Enable `prediction_data=False` if not needed
3. Process in batches if necessary

---

## Troubleshooting

### Issue: 90% anomalies
**Solution**: Increase `min_cluster_size_pct` to 0.03-0.05

### Issue: 0% anomalies
**Solution**: Decrease `min_cluster_size_pct` to 0.01

### Issue: Too many small clusters
**Solution**: Increase `min_samples` to 30-50

### Issue: Slow performance
**Solution**: 
- Use PCA instead of UMAP
- Reduce `pca_variance` to 0.90
- Increase `min_cluster_size_pct`

### Issue: UMAP not found
**Solution**: `pip install umap-learn`

---

## Advanced Usage

### Custom Preprocessing
```python
from preprocessing import LogPreprocessor

preprocessor = LogPreprocessor(
    null_threshold=0.7,
    correlation_threshold=0.95
)
X_scaled, features = preprocessor.preprocess(df)
```

### Custom Clustering
```python
from clustering import HDBSCANClusterer

clusterer = HDBSCANClusterer(
    min_cluster_size_pct=0.025,
    min_samples=15,
    metric='manhattan'
)
labels = clusterer.fit_predict(X)
```

### Run Single Experiment
```python
from experiments import ExperimentRunner

runner = ExperimentRunner('data/merged_output1.csv')
labels, metrics, df = runner.run_experiment(
    config_name='Custom Config',
    dim_reduction_mode='pca',
    metric='euclidean',
    min_cluster_size_pct=0.02,
    min_samples=20
)
```

---

## Files Overview

| File | Purpose |
|------|---------|
| `run_clustering.py` | Main production pipeline |
| `preprocessing.py` | Feature cleaning and scaling |
| `clustering.py` | HDBSCAN clustering logic |
| `experiments.py` | Multi-configuration testing |
| `clustering_config.json` | Configuration file |
| `CLUSTERING_GUIDE.md` | This documentation |

---

## Best Practices

1. ✅ Always run experiments first to find best config
2. ✅ Start with default PCA + Euclidean
3. ✅ Monitor anomaly percentage (target 5-20%)
4. ✅ Use ground truth evaluation if available
5. ✅ Save configuration for reproducibility
6. ✅ Check cluster stability metrics
7. ✅ Identify small/unstable clusters as anomaly candidates

---

## Production Deployment

### Step 1: Find Best Configuration
```bash
python -c "from experiments import ExperimentRunner; runner = ExperimentRunner('data/merged_output1.csv'); runner.run_all_experiments()"
```

### Step 2: Update Config
Edit `clustering_config.json` with best parameters

### Step 3: Run Production Pipeline
```bash
python run_clustering.py
```

### Step 4: Train Stage 2 Model
```bash
python train_model.py
```

### Step 5: Start Monitoring
```bash
python prometheus_exporter_phase2.py
```

---

**Status**: Production Ready ✅  
**Version**: 2.0  
**Last Updated**: 2026-02-20
