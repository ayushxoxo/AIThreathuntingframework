"""
Production-Ready HDBSCAN Clustering Pipeline
Configurable, scalable, and optimized for anomaly detection
"""

import os
import pandas as pd
import json
from preprocessing import LogPreprocessor, apply_dimensionality_reduction
from clustering import HDBSCANClusterer, save_cluster_files
from experiments import evaluate_with_ground_truth

def load_config(config_path='clustering_config.json'):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"[CONFIG] Loaded from {config_path}")
        return config
    except FileNotFoundError:
        print(f"[CONFIG] File not found, using defaults")
        return get_default_config()

def get_default_config():
    """Default configuration"""
    return {
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
            "pca_variance": 0.95,
            "umap_params": {
                "n_neighbors": 30,
                "min_dist": 0.1,
                "n_components": 10
            }
        },
        "clustering": {
            "min_cluster_size_pct": 0.02,
            "min_samples": 20,
            "metric": "euclidean",
            "cluster_selection_method": "eom",
            "prediction_data": true
        },
        "evaluation": {
            "has_ground_truth": false,
            "ground_truth_column": "label"
        }
    }

def save_default_config(config_path='clustering_config.json'):
    """Save default configuration to file"""
    config = get_default_config()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"[CONFIG] Default configuration saved to {config_path}")

def main():
    """
    Main production pipeline with per-host clustering
    """
    
    print("=" * 70)
    print("PRODUCTION HDBSCAN CLUSTERING PIPELINE")
    print("=" * 70)
    
    # Load configuration
    config = load_config()
    
    # Load data
    csv_path = config['data']['csv_path']
    output_dir = config['data']['output_dir']
    
    print(f"\n[LOADING] {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    
    print(f"[LOADED] {len(df)} rows, {len(df.columns)} columns")
    
    # Detect hosts
    host_col = None
    for col in ['hostName', 'SensorId', 'SourceIP', 'host']:
        if col in df.columns and df[col].notna().any():
            host_col = col
            break
    
    if host_col is None:
        print("\n[HOST DETECTION] No host column found, treating as single host")
        hosts = {'default': df}
    else:
        unique_hosts = df[host_col].dropna().unique()
        print(f"\n[HOST DETECTION] Found {len(unique_hosts)} unique hosts in column '{host_col}'")
        for i, host in enumerate(unique_hosts[:10], 1):
            print(f"  {i}. {host}")
        if len(unique_hosts) > 10:
            print(f"  ... and {len(unique_hosts) - 10} more hosts")
        
        # Segment by host
        hosts = {}
        for host_id in unique_hosts:
            host_df = df[df[host_col] == host_id].copy()
            if len(host_df) >= 100:  # Minimum logs per host
                hosts[str(host_id)] = host_df
            else:
                print(f"  [SKIP] {host_id}: Only {len(host_df)} logs (minimum 100 required)")
        
        print(f"\n[HOST SEGMENTATION] Processing {len(hosts)} hosts with sufficient data")
    
    # Process each host separately
    all_results = {}
    
    for host_id, host_df in hosts.items():
        print("\n" + "=" * 70)
        print(f"PROCESSING HOST: {host_id}")
        print("=" * 70)
        print(f"Logs for this host: {len(host_df)}")
        
        original_df = host_df.copy()
        
        # Extract ground truth if exists
        ground_truth = None
        if config['evaluation']['has_ground_truth']:
            gt_col = config['evaluation']['ground_truth_column']
            if gt_col in host_df.columns:
                ground_truth = host_df[gt_col].values
                host_df = host_df.drop(columns=[gt_col])
                print(f"[GROUND TRUTH] Extracted from column '{gt_col}'")
        
        # Preprocessing
        preprocessor = LogPreprocessor(
            null_threshold=config['preprocessing']['null_threshold'],
            correlation_threshold=config['preprocessing']['correlation_threshold'],
            high_cardinality_threshold=config['preprocessing']['high_cardinality_threshold']
        )
        
        X_scaled, feature_names = preprocessor.preprocess(host_df)
        
        # Dimensionality reduction
        dim_config = config['dimensionality_reduction']
        X_reduced, reducer = apply_dimensionality_reduction(
            X_scaled,
            mode=dim_config['mode'],
            pca_variance=dim_config.get('pca_variance', 0.95),
            umap_params=dim_config.get('umap_params')
        )
        
        # Clustering
        cluster_config = config['clustering']
        clusterer = HDBSCANClusterer(
            min_cluster_size_pct=cluster_config['min_cluster_size_pct'],
            min_samples=cluster_config['min_samples'],
            metric=cluster_config['metric'],
            cluster_selection_method=cluster_config['cluster_selection_method'],
            prediction_data=cluster_config['prediction_data']
        )
        
        labels = clusterer.fit_predict(X_reduced)
        metrics = clusterer.get_metrics(labels)
        clusterer.print_results(metrics)
        
        # Identify anomaly candidates
        anomaly_candidates = clusterer.identify_small_unstable_clusters(labels, metrics)
        
        # Save cluster files for this host
        save_cluster_files(original_df, labels, output_dir=output_dir, host_id=host_id)
        
        # Evaluation with ground truth
        if ground_truth is not None:
            eval_metrics = evaluate_with_ground_truth(labels, ground_truth)
        
        # Store results
        all_results[host_id] = {
            'n_logs': len(host_df),
            'n_clusters': int(metrics['n_clusters']),
            'n_anomalies': int(metrics['n_anomalies']),
            'anomaly_pct': float(metrics['anomaly_pct']),
            'n_anomaly_candidates': len(anomaly_candidates)
        }
    
    # Summary across all hosts
    print("\n" + "=" * 70)
    print("SUMMARY ACROSS ALL HOSTS")
    print("=" * 70)
    
    summary_df = pd.DataFrame.from_dict(all_results, orient='index')
    summary_df.index.name = 'host_id'
    print(summary_df.to_string())
    
    # Save summary
    summary = {
        'config': config,
        'total_hosts': len(hosts),
        'results_by_host': all_results,
        'totals': {
            'total_logs': int(summary_df['n_logs'].sum()),
            'total_clusters': int(summary_df['n_clusters'].sum()),
            'total_anomalies': int(summary_df['n_anomalies'].sum()),
            'avg_anomaly_pct': float(summary_df['anomaly_pct'].mean())
        }
    }
    
    os.makedirs('results', exist_ok=True)

    with open('results/clustering_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    summary_df.to_csv('results/clustering_summary_by_host.csv')
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"✅ Processed {len(hosts)} hosts")
    print(f"✅ Total logs: {summary['totals']['total_logs']:,}")
    print(f"✅ Total clusters: {summary['totals']['total_clusters']}")
    print(f"✅ Total anomalies: {summary['totals']['total_anomalies']:,}")
    print(f"✅ Average anomaly rate: {summary['totals']['avg_anomaly_pct']:.2f}%")
    print(f"✅ Cluster files saved to: {output_dir}")
    print(f"✅ Summary saved to: results/clustering_summary.json")
    print(f"✅ Per-host summary: results/clustering_summary_by_host.csv")
    print("=" * 70)

if __name__ == "__main__":
    # Uncomment to create default config file
    # save_default_config()
    
    main()
