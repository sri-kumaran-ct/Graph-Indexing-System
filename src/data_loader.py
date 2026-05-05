"""
Graph Data Loader Module
Handles loading graph datasets from CSV files and edge lists.
"""

import pandas as pd
import dask.dataframe as dd
from typing import Tuple, Optional, List
import os


class GraphDataLoader:
    """
    Loads graph data from various file formats (CSV, edge lists).
    Supports both pandas (small files) and Dask (large files) backends.
    """
    
    def __init__(self, use_dask: bool = True, chunk_size: int = 100000):
        """
        Initialize the data loader.
        
        Args:
            use_dask: Whether to use Dask for large file processing
            chunk_size: Chunk size for Dask processing (number of rows)
        """
        self.use_dask = use_dask
        self.chunk_size = chunk_size
    
    def load_edge_list(self, file_path: str, 
                      source_col: str = 'source',
                      target_col: str = 'target',
                      weight_col: Optional[str] = None,
                      delimiter: str = ',') -> pd.DataFrame:
        """
        Load graph data from an edge list file.
        
        Args:
            file_path: Path to the edge list file
            source_col: Name of the source node column
            target_col: Name of the target node column
            weight_col: Optional name of the weight column
            delimiter: Delimiter used in the file (default: comma for CSV)
        
        Returns:
            DataFrame with columns: source, target, (weight if provided)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if self.use_dask:
            # Use Dask for large files
            df = dd.read_csv(file_path, delimiter=delimiter, 
                           blocksize=self.chunk_size * 1024)  # blocksize in bytes
            
            # Ensure required columns exist
            required_cols = [source_col, target_col]
            if weight_col:
                required_cols.append(weight_col)
            
            # Check which columns are available
            available_cols = df.columns.tolist()
            missing_cols = [col for col in required_cols if col not in available_cols]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}. Available columns: {available_cols}")
            
            # Select only required columns
            selected_cols = [col for col in required_cols if col in available_cols]
            df = df[selected_cols]
            
            # Rename columns to standard names
            df = df.rename(columns={source_col: 'source', target_col: 'target'})
            if weight_col and weight_col in df.columns:
                df = df.rename(columns={weight_col: 'weight'})
            
            # Convert to pandas for further processing (or keep as Dask)
            return df.compute()
        else:
            # Use pandas for smaller files
            df = pd.read_csv(file_path, delimiter=delimiter)
            
            # Select and rename columns
            required_cols = [source_col, target_col]
            if weight_col:
                required_cols.append(weight_col)
            
            df = df[[col for col in required_cols if col in df.columns]]
            df = df.rename(columns={source_col: 'source', target_col: 'target'})
            if weight_col and weight_col in df.columns:
                df = df.rename(columns={weight_col: 'weight'})
            
            return df
    
    def load_adjacency_list(self, file_path: str, delimiter: str = ',') -> pd.DataFrame:
        """
        Load graph data from an adjacency list format.
        Expected format: node_id, neighbor1, neighbor2, ...
        
        Args:
            file_path: Path to the adjacency list file
            delimiter: Delimiter used in the file
        
        Returns:
            DataFrame in edge list format (source, target)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        edges = []
        
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split(delimiter)
                if len(parts) < 2:
                    continue
                
                source = parts[0].strip()
                for target in parts[1:]:
                    if target.strip():
                        edges.append({'source': source, 'target': target.strip()})
        
        return pd.DataFrame(edges)
    
    def validate_graph_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that the loaded graph data has required columns.
        
        Args:
            df: DataFrame to validate
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        required_cols = ['source', 'target']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check for empty dataframe
        if df.empty:
            raise ValueError("Graph data is empty")
        
        # Remove any rows with missing source or target
        df_clean = df.dropna(subset=['source', 'target'])
        if len(df_clean) < len(df):
            print(f"Warning: Removed {len(df) - len(df_clean)} rows with missing values")
        
        return True

