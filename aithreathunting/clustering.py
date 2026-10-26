import pandas as pd
import numpy as np
import hdbscan
from hdbscan import HDBSCAN
import os

class HDBSCANClusterer:
    """Production-ready HDBSCAN clustering with configurable parameters"""
    
    def __init__(self, 
                 min_cluster_size_pct=0.02,
                 min_samples=20,
                 metric='euclidean',
                 cluster_selection_method='eom',
                 prediction_data=True):
        """
        Args:
            min_cluster_size_pct: Percentage of dataset (0.01-0.03 recommended)
            min_samples: Density threshold (10, 20, 50)
            metric: 'euclidean', 'manhattan', 'cosine'
            cluster_selection_method: 'eom' (default)
            prediction_data: Enable approximate_predict
        """
        self.min_cluster_size_pct = min_cluster_size_pct
        self.min_samples = min_samples
        self.metric = metric
        self.cluster_selection_method = cluster_selection_method
        self.prediction_data = prediction_data
        self.clusterer = None
        
    def fit_predict(self, X):
        """Fit HDBSCAN and return labels"""
        
        # Dynamic min_cluster_size
        min_cluster_size = max(int(self.min_cluster_size_pct * len(X)), 50)
        
        print("=" * 70)
        print("HDBSCAN CLUSTERING")
        print("=" * 70)
        print(f"[CONFIG] Dataset size: {len(X)}")
        print(f"[CONFIG] min_cluster_size: {min_cluster_size} ({self.min_cluster_size_pct*100:.1f}% of data)")
        print(f"[CONFIG] min_samples: {self.min_samples}")
        print(f"[CONFIG] metric: {self.metric}")
        print(f"[CONFIG] cluster_selection_method: {self.cluster_selection_method}")
        
        self.clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=self.min_samples,
            metric=self.metric,
            cluster_selection_method=self.cluster_selection_method,
            prediction_data=self.prediction_data,
            core_dist_n_jobs=-1
        )
        
        labels = self.clusterer.fit_predict(X)
        
        return labels
    
    def get_metrics(self, labels):
        """Calculate clustering metrics"""
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_anomalies = int((labels == -1).sum())
        anomaly_pct = (n_anomalies / len(labels)) * 100
        
        # Cluster sizes
        cluster_sizes = {}
        for label in unique_labels:
            if label != -1:
                cluster_sizes[label] = int((labels == label).sum())
        
        metrics = {
            'n_clusters': n_clusters,
            'n_anomalies': n_anomalies,
            'anomaly_pct': anomaly_pct,
            'cluster_sizes': cluster_sizes,
            'outlier_scores': self.clusterer.outlier_scores_ if hasattr(self.clusterer, 'outlier_scores_') else None,
            'probabilities': self.clusterer.probabilities_ if hasattr(self.clusterer, 'probabilities_') else None,
            'cluster_persistence': self.clusterer.cluster_persistence_ if hasattr(self.clusterer, 'cluster_persistence_') else None
        }
        
        return metrics
    
    def print_results(self, metrics):
        """Print clustering results"""
        print("\n" + "=" * 70)
        print("CLUSTERING RESULTS")
        print("=" * 70)
        print(f"Number of clusters: {metrics['n_clusters']}")
        print(f"Number of anomalies (-1): {metrics['n_anomalies']}")
        print(f"Anomaly percentage: {metrics['anomaly_pct']:.2f}%")
        
        if metrics['cluster_sizes']:
            print(f"\nCluster size distribution:")
            sorted_clusters = sorted(metrics['cluster_sizes'].items(), key=lambda x: x[1], reverse=True)
            for cluster_id, size in sorted_clusters[:10]:  # Top 10
                print(f"  Cluster {cluster_id}: {size} points")
            
            if len(sorted_clusters) > 10:
                print(f"  ... and {len(sorted_clusters) - 10} more clusters")
        
        if metrics['outlier_scores'] is not None:
            print(f"\nOutlier score stats:")
            print(f"  Mean: {metrics['outlier_scores'].mean():.3f}")
            print(f"  Std: {metrics['outlier_scores'].std():.3f}")
            print(f"  Max: {metrics['outlier_scores'].max():.3f}")
        
        # Stability check
        if metrics['anomaly_pct'] > 25:
            print(f"\n⚠️  WARNING: Anomaly rate too high ({metrics['anomaly_pct']:.1f}%)")
            print("   Consider: Increase min_cluster_size or decrease min_samples")
        elif metrics['anomaly_pct'] < 1:
            print(f"\n⚠️  WARNING: Anomaly rate too low ({metrics['anomaly_pct']:.1f}%)")
            print("   Consider: Decrease min_cluster_size or increase min_samples")
        else:
            print(f"\n✅ Anomaly rate is balanced ({metrics['anomaly_pct']:.1f}%)")
    
    def identify_small_unstable_clusters(self, labels, metrics, size_threshold=100, persistence_threshold=0.2):
        """Identify small/unstable clusters as anomaly candidates"""
        anomaly_candidates = set()
        
        # Small clusters
        for cluster_id, size in metrics['cluster_sizes'].items():
            if size < size_threshold:
                anomaly_candidates.add(cluster_id)
        
        # Unstable clusters
        if metrics['cluster_persistence'] is not None:
            for i, persistence in enumerate(metrics['cluster_persistence']):
                if persistence < persistence_threshold:
                    anomaly_candidates.add(i)
        
        if anomaly_candidates:
            print(f"\n[ANOMALY CANDIDATES] {len(anomaly_candidates)} small/unstable clusters identified")
            print(f"  Cluster IDs: {sorted(list(anomaly_candidates))[:10]}")
        
        return anomaly_candidates


def save_cluster_files(df, labels, output_dir='data/clusters', host_id='default'):
    """Save cluster files to normal/ and anomaly/ subdirectories"""
    
    normal_dir = os.path.join(output_dir, 'normal')
    anomaly_dir = os.path.join(output_dir, 'anomaly')
    
    os.makedirs(normal_dir, exist_ok=True)
    os.makedirs(anomaly_dir, exist_ok=True)
    
    df_copy = df.copy()
    df_copy['cluster_label'] = labels
    
    unique_labels = set(labels)
    
    for label in unique_labels:
        cluster_df = df_copy[df_copy['cluster_label'] == label]
        
        if label == -1:
            filename = os.path.join(anomaly_dir, f"host_{host_id}_cluster_-1.csv")
        else:
            filename = os.path.join(normal_dir, f"host_{host_id}_cluster_{label}.csv")
        
        cluster_df.to_csv(filename, index=False)
    
    print(f"\n[OUTPUT] Saved {len(unique_labels)} cluster files to {output_dir}")
