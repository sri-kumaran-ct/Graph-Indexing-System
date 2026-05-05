"""
Main Graph Database Class
Integrates all components: loading, preprocessing, indexing, querying, and security.
"""

import os
import pandas as pd
from typing import Optional, Dict
from src.data_loader import GraphDataLoader
from src.preprocessing import GraphPreprocessor
from src.indexing import GraphIndex
from src.query_engine import QueryEngine
from src.security import AccessControl, Permission


class GraphDatabase:
    """
    Main graph database class that integrates all components.
    Provides a unified interface for graph operations.
    """
    
    def __init__(self, enable_security: bool = True):
        """
        Initialize graph database.
        
        Args:
            enable_security: Whether to enable access control
        """
        self.loader = GraphDataLoader()
        self.preprocessor = GraphPreprocessor()
        self.index = GraphIndex()
        self.query_engine = QueryEngine(self.index)
        self.access_control = AccessControl() if enable_security else None
        self.is_indexed = False
    
    def load_graph(self, file_path: str,
                   source_col: str = 'source',
                   target_col: str = 'target',
                   weight_col: Optional[str] = None,
                   delimiter: str = ',',
                   use_dask: bool = True) -> pd.DataFrame:
        """
        Load graph data from file.
        
        Args:
            file_path: Path to graph data file
            source_col: Name of source column
            target_col: Name of target column
            weight_col: Optional weight column
            delimiter: File delimiter
            use_dask: Whether to use Dask for large files
        
        Returns:
            Loaded DataFrame
        """
        self.loader.use_dask = use_dask
        df = self.loader.load_edge_list(
            file_path, source_col, target_col, weight_col, delimiter
        )
        self.loader.validate_graph_data(df)
        return df
    
    def preprocess_graph(self, df: pd.DataFrame,
                        normalize: bool = True,
                        clean: bool = True,
                        **clean_kwargs) -> pd.DataFrame:
        """
        Preprocess graph data.
        
        Args:
            df: Raw graph DataFrame
            normalize: Whether to normalize node IDs
            clean: Whether to clean data
            **clean_kwargs: Additional cleaning options
        
        Returns:
            Preprocessed DataFrame
        """
        return self.preprocessor.preprocess(df, normalize, clean, **clean_kwargs)
    
    def build_index(self, df: pd.DataFrame, directed: bool = True, weight_col: Optional[str] = None):
        """
        Build graph indexes from preprocessed data.
        
        Args:
            df: Preprocessed graph DataFrame
            directed: Whether graph is directed
            weight_col: Optional weight column name
        """
        # Auto-detect weight column if not specified
        if weight_col is None and 'weight' in df.columns:
            weight_col = 'weight'
        
        self.index.build_from_dataframe(df, directed=directed, weight_col=weight_col)
        self.is_indexed = True
        print("Graph index built successfully")
    
    def load_and_index(self, file_path: str,
                      source_col: str = 'source',
                      target_col: str = 'target',
                      normalize: bool = True,
                      clean: bool = True,
                      directed: bool = True,
                      **kwargs) -> Dict:
        """
        Complete pipeline: load, preprocess, and index graph.
        
        Args:
            file_path: Path to graph data file
            source_col: Name of source column
            target_col: Name of target column
            normalize: Whether to normalize node IDs
            clean: Whether to clean data
            directed: Whether graph is directed
            **kwargs: Additional arguments for loading/preprocessing
        
        Returns:
            Dictionary with processing statistics
        """
        print(f"Loading graph from {file_path}...")
        
        # Extract weight_col and other load_graph specific params from kwargs
        weight_col = kwargs.pop('weight_col', None)
        use_dask = kwargs.pop('use_dask', True)
        delimiter = kwargs.pop('delimiter', ',')
        
        # Auto-detect weight column if not provided
        if weight_col is None:
            # Try to detect from file first by reading a sample
            import pandas as pd
            try:
                sample_df = pd.read_csv(file_path, nrows=1)
                if 'weight' in sample_df.columns:
                    weight_col = 'weight'
                    print(f"Auto-detected weight column: {weight_col}")
            except:
                pass
        
        df = self.load_graph(file_path, source_col, target_col, 
                            weight_col=weight_col, delimiter=delimiter, use_dask=use_dask)
        
        print("Preprocessing graph...")
        df_processed = self.preprocess_graph(df, normalize, clean, weight_col=weight_col)
        
        # Ensure weight column name is correct after preprocessing
        if weight_col is None and 'weight' in df_processed.columns:
            weight_col = 'weight'
        
        print("Building index...")
        self.build_index(df_processed, directed=directed, weight_col=weight_col)
        
        stats = self.index.get_statistics()
        return {
            'status': 'success',
            'statistics': stats
        }
    
    def query(self, user_id: str, query_type: str, **kwargs) -> Dict:
        """
        Execute a query with security checks.
        
        Args:
            user_id: User identifier
            query_type: Type of query ('lookup', 'neighbors', 'path', 'common_neighbors', 'stats')
            **kwargs: Query-specific arguments
        
        Returns:
            Query result dictionary
        """
        # Check if user exists (if security enabled)
        if self.access_control:
            if user_id not in self.access_control.users:
                return {'error': 'User not found', 'user_id': user_id}
            
            # Check rate limit
            allowed, message = self.access_control.check_rate_limit(user_id)
            if not allowed:
                return {'error': 'Rate limit exceeded', 'message': message}
            
            # Record query
            self.access_control.record_query(user_id)
        
        # Check if graph is indexed
        if not self.is_indexed:
            return {'error': 'Graph not indexed. Please load and index graph first.'}
        
        # Execute query based on type
        if query_type == 'lookup':
            node_id = kwargs.get('node_id')
            if node_id is None:
                return {'error': 'node_id required for lookup query'}
            
            # Check if node is blocked
            if self.access_control and self.access_control.is_node_blocked(node_id):
                return {'error': 'Access denied', 'message': f'Node {node_id} is blocked'}
            
            return self.query_engine.lookup_node(node_id)
        
        elif query_type == 'neighbors':
            node_id = kwargs.get('node_id')
            direction = kwargs.get('direction', 'out')
            limit = kwargs.get('limit')
            
            if node_id is None:
                return {'error': 'node_id required for neighbors query'}
            
            if self.access_control and self.access_control.is_node_blocked(node_id):
                return {'error': 'Access denied', 'message': f'Node {node_id} is blocked'}
            
            return self.query_engine.get_neighbors(node_id, direction, limit)
        
        elif query_type == 'path':
            source = kwargs.get('source')
            target = kwargs.get('target')
            max_depth = kwargs.get('max_depth', 10)
            directed = kwargs.get('directed', True)
            use_weights = kwargs.get('use_weights', True)  # Use weights if available
            
            if source is None or target is None:
                return {'error': 'source and target required for path query'}
            
            if self.access_control:
                if self.access_control.is_node_blocked(source) or self.access_control.is_node_blocked(target):
                    return {'error': 'Access denied', 'message': 'One or both nodes are blocked'}
                if self.access_control.is_edge_blocked(source, target):
                    return {'error': 'Access denied', 'message': 'Edge is blocked'}
            
            return self.query_engine.find_path(source, target, max_depth, directed, use_weights)
        
        elif query_type == 'common_neighbors':
            node1 = kwargs.get('node1')
            node2 = kwargs.get('node2')
            direction = kwargs.get('direction', 'out')
            
            if node1 is None or node2 is None:
                return {'error': 'node1 and node2 required for common_neighbors query'}
            
            if self.access_control:
                if self.access_control.is_node_blocked(node1) or self.access_control.is_node_blocked(node2):
                    return {'error': 'Access denied', 'message': 'One or both nodes are blocked'}
            
            return self.query_engine.get_common_neighbors(node1, node2, direction)
        
        elif query_type == 'stats':
            node_id = kwargs.get('node_id')
            if node_id is None:
                return {'error': 'node_id required for stats query'}
            
            if self.access_control and self.access_control.is_node_blocked(node_id):
                return {'error': 'Access denied', 'message': f'Node {node_id} is blocked'}
            
            return self.query_engine.get_node_statistics(node_id)
        
        else:
            return {'error': f'Unknown query type: {query_type}'}
    
    def save_index(self, file_path: str):
        """
        Save graph index to disk.
        
        Args:
            file_path: Path to save index
        """
        self.index.save(file_path)
    
    def load_index(self, file_path: str):
        """
        Load graph index from disk.
        
        Args:
            file_path: Path to index file
        """
        self.index.load(file_path)
        self.is_indexed = True
    
    def get_graph_statistics(self) -> Dict:
        """
        Get overall graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        if not self.is_indexed:
            return {'error': 'Graph not indexed'}
        
        return self.index.get_statistics()

