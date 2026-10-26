import os
import pandas as pd
import numpy as np
from preprocessing import LogPreprocessor, apply_dimensionality_reduction
from clustering import HDBSCANClusterer
import json

class ExperimentRunner:
    """Run multiple experimental configurations"""
    
    def __init__(self, csv_path, output_dir='data/clusters'):
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.results = []
        
    def run_experiment(self, config_name, dim_reduction_mode, metric, 
                      min_cluster_size_pct=0.02, min_samples=20, pca_variance=0.95):
        """Run single experiment configuration"""
        
        print("\n" + "=" * 70)
        print(f"EXPERIMENT: {config_name}")
        print("=" * 70)
        
        # Load data
        print(f"[LOADING] {self.csv_path}")
        df = pd.read_csv(self.csv_path, low_memory=False)
        original_df = df.copy()
        
        # Preprocess
        preprocessor = LogPreprocessor()
        X_scaled, feature_names = preprocessor.preprocess(df)
        
        # Dimensionality reduction
        X_reduced, reducer = apply_dimensionality_reduction(
            X_scaled, 
            mode=dim_reduction_mode,
            pca_variance=pca_variance
        )
        
        # Clustering
        clusterer = HDBSCANClusterer(
            min_cluster_size_pct=min_cluster_size_pct,
            min_samples=min_samples,
            metric=metric
        )
        
        labels = clusterer.fit_predict(X_reduced)
        metrics = clusterer.get_metrics(labels)
        clusterer.print_results(metrics)
        
        # Identify anomaly candidates
        anomaly_candidates = clusterer.identify_small_unstable_clusters(labels, metrics)
        
        # Store results
        result = {
            'config_name': config_name,
            'dim_reduction': dim_reduction_mode,
            'metric': metric,
            'min_cluster_size_pct': min_cluster_size_pct,
            'min_samples': min_samples,
            'n_clusters': metrics['n_clusters'],
            'n_anomalies': metrics['n_anomalies'],
            'anomaly_pct': metrics['anomaly_pct'],
            'n_anomaly_candidates': len(anomaly_candidates)
        }
        
        self.results.append(result)
        
        return labels, metrics, original_df
    
    def run_all_experiments(self):
        """Run all 4 experimental configurations"""
        
        configs = [
            {
                'name': 'Config 1: PCA + Euclidean',
                'dim_reduction': 'pca',
                'metric': 'euclidean',
                'pca_variance': 0.95
            },
            {
                'name': 'Config 2: PCA + Manhattan',
                'dim_reduction': 'pca',
                'metric': 'manhattan',
                'pca_variance': 0.95
            },
            {
                'name': 'Config 3: UMAP + Euclidean',
                'dim_reduction': 'umap',
                'metric': 'euclidean',
                'pca_variance': None
            },
            {
                'name': 'Config 4: Scaled Only + Euclidean',
                'dim_reduction': 'none',
                'metric': 'euclidean',
                'pca_variance': None
            }
        ]
        
        for config in configs:
            try:
                labels, metrics, df = self.run_experiment(
                    config_name=config['name'],
                    dim_reduction_mode=config['dim_reduction'],
                    metric=config['metric'],
                    pca_variance=config.get('pca_variance', 0.95)
                )
            except Exception as e:
                print(f"\n❌ {config['name']} FAILED: {e}")
                continue
        
        # Print comparison
        self.print_comparison()
    
    def print_comparison(self):
        """Print comparison of all experiments"""
        print("\n" + "=" * 70)
        print("EXPERIMENT COMPARISON")
        print("=" * 70)
        
        df_results = pd.DataFrame(self.results)
        
        print(df_results.to_string(index=False))
        
        # Save results
        os.makedirs('results', exist_ok=True)
        df_results.to_csv('results/experiment_results.csv', index=False)
        print(f"\n[SAVED] Results saved to results/experiment_results.csv")
        
        # Recommendations
        print("\n" + "=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)
        
        # Best anomaly rate (5-20%)
        df_results['anomaly_score'] = df_results['anomaly_pct'].apply(
            lambda x: abs(x - 10)  # Target 10%
        )
        
        best_config = df_results.loc[df_results['anomaly_score'].idxmin()]
        
        print(f"✅ Best configuration: {best_config['config_name']}")
        print(f"   - Anomaly rate: {best_config['anomaly_pct']:.2f}%")
        print(f"   - Clusters: {best_config['n_clusters']}")
        print(f"   - Anomalies: {best_config['n_anomalies']}")


def evaluate_with_ground_truth(labels, ground_truth_labels):
    """Evaluate clustering against ground truth"""
    from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
    
    print("\n" + "=" * 70)
    print("EVALUATION WITH GROUND TRUTH")
    print("=" * 70)
    
    # Convert cluster labels to binary (anomaly vs normal)
    predicted_anomaly = (labels == -1).astype(int)
    
    precision = precision_score(ground_truth_labels, predicted_anomaly)
    recall = recall_score(ground_truth_labels, predicted_anomaly)
    f1 = f1_score(ground_truth_labels, predicted_anomaly)
    
    print(f"Precision (anomaly class): {precision:.3f}")
    print(f"Recall (attack detection): {recall:.3f}")
    print(f"F1 Score: {f1:.3f}")
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(ground_truth_labels, predicted_anomaly)
    print(cm)
    
    return {'precision': precision, 'recall': recall, 'f1': f1}
