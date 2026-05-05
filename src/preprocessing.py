"""
Preprocessing Module
Handles cleaning, normalization, and efficient storage of graph data using Dask.
"""

import pandas as pd
import dask.dataframe as dd
from typing import Dict, Optional, Tuple
import numpy as np
import pickle
import os


class GraphPreprocessor:
    """
    Preprocesses graph data: cleaning, normalization, and storage optimization.
    Uses Dask for handling large datasets efficiently.
    """
    
    def __init__(self, use_dask: bool = True):
        """
        Initialize the preprocessor.
        
        Args:
            use_dask: Whether to use Dask for processing
        """
        self.use_dask = use_dask
        self.node_mapping = {}  # Maps original node IDs to normalized integer IDs
        self.reverse_mapping = {}  # Maps normalized IDs back to original IDs
    
    def normalize_node_ids(self, df: pd.DataFrame, 
                          source_col: str = 'source',
                          target_col: str = 'target',
                          weight_col: Optional[str] = None) -> pd.DataFrame:
        """
        Normalize node IDs to consecutive integers for efficient storage.
        
        Args:
            df: DataFrame with graph edges
            source_col: Name of source column
            target_col: Name of target column
            weight_col: Optional weight column name (preserved, not normalized)
        
        Returns:
            DataFrame with normalized node IDs (weight column preserved if present)
        """
        # Get all unique nodes
        all_nodes = pd.concat([df[source_col], df[target_col]]).unique()
        
        # Create mapping from original IDs to normalized integer IDs
        self.node_mapping = {node: idx for idx, node in enumerate(sorted(all_nodes))}
        self.reverse_mapping = {idx: node for node, idx in self.node_mapping.items()}
        
        # Apply mapping
        df_normalized = df.copy()
        df_normalized[source_col] = df_normalized[source_col].map(self.node_mapping)
        df_normalized[target_col] = df_normalized[target_col].map(self.node_mapping)
        
        # Convert to appropriate integer types
        df_normalized[source_col] = df_normalized[source_col].astype(np.int32)
        df_normalized[target_col] = df_normalized[target_col].astype(np.int32)
        
        # Weight column is preserved as-is (not normalized)
        
        return df_normalized
    
    def clean_data(self, df: pd.DataFrame,
                   remove_self_loops: bool = True,
                   remove_duplicates: bool = True,
                   remove_isolated: bool = False) -> pd.DataFrame:
        """
        Clean graph data by removing self-loops, duplicates, and optionally isolated nodes.
        
        Args:
            df: DataFrame with graph edges
            remove_self_loops: Remove edges where source == target
            remove_duplicates: Remove duplicate edges
            remove_isolated: Remove nodes with no connections
        
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        
        # Remove self-loops
        if remove_self_loops:
            initial_count = len(df_clean)
            df_clean = df_clean[df_clean['source'] != df_clean['target']]
            removed = initial_count - len(df_clean)
            if removed > 0:
                print(f"Removed {removed} self-loops")
        
        # Remove duplicates
        if remove_duplicates:
            initial_count = len(df_clean)
            df_clean = df_clean.drop_duplicates(subset=['source', 'target'])
            removed = initial_count - len(df_clean)
            if removed > 0:
                print(f"Removed {removed} duplicate edges")
        
        # Remove isolated nodes (nodes with no edges)
        if remove_isolated:
            all_nodes = set(df_clean['source'].unique()) | set(df_clean['target'].unique())
            connected_nodes = set(df_clean['source'].unique()) & set(df_clean['target'].unique())
            isolated = all_nodes - connected_nodes
            if isolated:
                print(f"Found {len(isolated)} isolated nodes (not removed by default)")
        
        return df_clean
    
    def preprocess(self, df: pd.DataFrame,
                   normalize: bool = True,
                   clean: bool = True,
                   weight_col: Optional[str] = None,
                   **clean_kwargs) -> pd.DataFrame:
        """
        Complete preprocessing pipeline: normalize and clean.
        
        Args:
            df: Raw graph DataFrame
            normalize: Whether to normalize node IDs
            clean: Whether to clean the data
            weight_col: Optional weight column name (preserved through preprocessing)
            **clean_kwargs: Additional arguments for clean_data
        
        Returns:
            Preprocessed DataFrame
        """
        df_processed = df.copy()
        
        if normalize:
            print("Normalizing node IDs...")
            df_processed = self.normalize_node_ids(df_processed, weight_col=weight_col)
            print(f"Normalized {len(self.node_mapping)} unique nodes")
        
        if clean:
            print("Cleaning data...")
            df_processed = self.clean_data(df_processed, **clean_kwargs)
            print(f"Final edge count: {len(df_processed)}")
        
        return df_processed
    
    def save_preprocessed(self, df: pd.DataFrame, output_path: str,
                         save_mapping: bool = True, mapping_path: Optional[str] = None):
        """
        Save preprocessed graph data and node mappings.
        
        Args:
            df: Preprocessed DataFrame
            output_path: Path to save the preprocessed data (CSV or Parquet)
            save_mapping: Whether to save node mappings
            mapping_path: Path to save mappings (default: output_path + '_mapping.pkl')
        """
        # Save preprocessed data
        if output_path.endswith('.parquet'):
            df.to_parquet(output_path, index=False)
        else:
            df.to_csv(output_path, index=False)
        
        print(f"Saved preprocessed data to {output_path}")
        
        # Save node mappings
        if save_mapping and self.node_mapping:
            if mapping_path is None:
                mapping_path = output_path.replace('.csv', '_mapping.pkl').replace('.parquet', '_mapping.pkl')
            
            with open(mapping_path, 'wb') as f:
                pickle.dump({
                    'node_mapping': self.node_mapping,
                    'reverse_mapping': self.reverse_mapping
                }, f)
            
            print(f"Saved node mappings to {mapping_path}")
    
    def load_mapping(self, mapping_path: str) -> Dict:
        """
        Load node mappings from file.
        
        Args:
            mapping_path: Path to the mapping file
        
        Returns:
            Dictionary with 'node_mapping' and 'reverse_mapping'
        """
        with open(mapping_path, 'rb') as f:
            mappings = pickle.load(f)
        
        self.node_mapping = mappings['node_mapping']
        self.reverse_mapping = mappings['reverse_mapping']
        
        return mappings

