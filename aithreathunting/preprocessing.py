import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

class LogPreprocessor:
    """Production-ready log preprocessing with configurable options"""
    
    def __init__(self, 
                 null_threshold=0.5,
                 correlation_threshold=0.9,
                 high_cardinality_threshold=100):
        self.null_threshold = null_threshold
        self.correlation_threshold = correlation_threshold
        self.high_cardinality_threshold = high_cardinality_threshold
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.dropped_columns = []
        
    def clean_features(self, df):
        """Remove constant, high-null, and highly correlated features"""
        print(f"[CLEANUP] Initial shape: {df.shape}")
        
        # Drop constant columns
        constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
        df = df.drop(columns=constant_cols)
        print(f"[CLEANUP] Dropped {len(constant_cols)} constant columns")
        
        # Drop high null percentage columns
        null_pct = df.isnull().sum() / len(df)
        high_null_cols = null_pct[null_pct > self.null_threshold].index.tolist()
        df = df.drop(columns=high_null_cols)
        print(f"[CLEANUP] Dropped {len(high_null_cols)} high-null columns (>{self.null_threshold*100}%)")
        
        # Drop timestamp columns (unless engineered)
        timestamp_cols = [col for col in df.columns if 'timestamp' in col.lower() or 'time' in col.lower()]
        df = df.drop(columns=timestamp_cols, errors='ignore')
        print(f"[CLEANUP] Dropped {len(timestamp_cols)} timestamp columns")
        
        self.dropped_columns = constant_cols + high_null_cols + timestamp_cols
        
        return df
    
    def encode_categorical(self, df):
        """Encode categorical features with label/frequency encoding"""
        print(f"[ENCODING] Processing categorical features")
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        for col in categorical_cols:
            n_unique = df[col].nunique()
            
            if n_unique <= self.high_cardinality_threshold:
                # Label encoding for low cardinality
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
                print(f"  - {col}: Label encoded ({n_unique} unique values)")
            else:
                # Frequency encoding for high cardinality
                freq_map = df[col].value_counts(normalize=True).to_dict()
                df[col] = df[col].map(freq_map).fillna(0)
                print(f"  - {col}: Frequency encoded ({n_unique} unique values)")
        
        return df
    
    def remove_correlated_features(self, df):
        """Remove highly correlated features"""
        print(f"[CORRELATION] Checking for highly correlated features")
        
        # Only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.shape[1] < 2:
            return df
        
        corr_matrix = numeric_df.corr().abs()
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        
        to_drop = [col for col in upper_triangle.columns 
                   if any(upper_triangle[col] > self.correlation_threshold)]
        
        df = df.drop(columns=to_drop)
        print(f"[CORRELATION] Dropped {len(to_drop)} highly correlated features")
        
        return df
    
    def scale_features(self, df):
        """Mandatory scaling with float32 conversion"""
        print(f"[SCALING] Standardizing features")
        
        # Ensure all numeric
        df = df.select_dtypes(include=[np.number])
        
        # Fill missing values
        df = df.fillna(0)
        
        # Convert to float32 for memory efficiency
        df = df.astype(np.float32)
        
        # Scale
        X_scaled = self.scaler.fit_transform(df)
        
        print(f"[SCALING] Final shape: {X_scaled.shape}, dtype: {X_scaled.dtype}")
        
        return X_scaled, df.columns.tolist()
    
    def preprocess(self, df):
        """Complete preprocessing pipeline"""
        print("=" * 70)
        print("PREPROCESSING PIPELINE")
        print("=" * 70)
        
        # Step 1: Clean features
        df = self.clean_features(df)
        
        # Step 2: Encode categorical
        df = self.encode_categorical(df)
        
        # Step 3: Remove correlated features
        df = self.remove_correlated_features(df)
        
        # Step 4: Scale (mandatory)
        X_scaled, feature_names = self.scale_features(df)
        
        return X_scaled, feature_names


def apply_dimensionality_reduction(X, mode='pca', pca_variance=0.95, umap_params=None):
    """
    Apply dimensionality reduction
    
    Mode A: PCA (default)
    Mode B: UMAP (advanced)
    """
    print("=" * 70)
    print(f"DIMENSIONALITY REDUCTION: {mode.upper()}")
    print("=" * 70)
    
    if mode == 'pca':
        n_components = min(int(pca_variance * X.shape[1]) if pca_variance < 1 else pca_variance, 
                          X.shape[1], X.shape[0] - 1)
        
        print(f"[PCA] Target variance: {pca_variance if pca_variance < 1 else 'N/A'}")
        pca = PCA(n_components=pca_variance if pca_variance < 1 else n_components, random_state=42)
        X_reduced = pca.fit_transform(X)
        
        explained_var = pca.explained_variance_ratio_.sum()
        print(f"[PCA] Components: {X_reduced.shape[1]}, Variance retained: {explained_var:.2%}")
        
        return X_reduced, pca
    
    elif mode == 'umap':
        try:
            import umap
        except ImportError:
            print("[ERROR] UMAP not installed. Run: pip install umap-learn")
            print("[FALLBACK] Using PCA instead")
            return apply_dimensionality_reduction(X, mode='pca', pca_variance=pca_variance)
        
        if umap_params is None:
            umap_params = {'n_neighbors': 30, 'min_dist': 0.1, 'n_components': 10}
        
        print(f"[UMAP] Parameters: {umap_params}")
        reducer = umap.UMAP(**umap_params, random_state=42)
        X_reduced = reducer.fit_transform(X)
        
        print(f"[UMAP] Reduced to {X_reduced.shape[1]} dimensions")
        
        return X_reduced, reducer
    
    elif mode == 'none':
        print("[NONE] No dimensionality reduction applied")
        return X, None
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'pca', 'umap', or 'none'")
