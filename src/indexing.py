"""
Indexing Module
Builds lightweight indexes for fast node and neighbor lookup.
"""

import pandas as pd
import numpy as np
from typing import Dict, Set, List, Optional
from collections import defaultdict
import pickle
import os


class GraphIndex:
    """
    Efficient indexing system for graph data.
    Maintains indexes for fast node and neighbor lookups.
    """
    
    def __init__(self):
        """Initialize empty indexes."""
        self.adjacency_list = defaultdict(set)  # node -> set of neighbors
        self.reverse_adjacency = defaultdict(set)  # node -> set of nodes pointing to it
        self.edge_weights = {}  # (source, target) -> weight
        self.node_degrees = {}  # node -> degree
        self.edge_count = 0
        self.node_count = 0
        self.has_weights = False  # Whether graph has edge weights
    
    def build_from_dataframe(self, df: pd.DataFrame,
                            source_col: str = 'source',
                            target_col: str = 'target',
                            weight_col: Optional[str] = None,
                            directed: bool = True):
        """
        Build indexes from a DataFrame of edges.
        
        Args:
            df: DataFrame with graph edges
            source_col: Name of source column
            target_col: Name of target column
            weight_col: Optional name of weight column
            directed: Whether the graph is directed
        """
        print("Building graph indexes...")
        
        # Clear existing indexes
        self.adjacency_list.clear()
        self.reverse_adjacency.clear()
        self.edge_weights.clear()
        self.node_degrees = {}
        
        # Check if weights are available
        self.has_weights = weight_col is not None and weight_col in df.columns
        
        # Build adjacency lists
        for _, row in df.iterrows():
            source = row[source_col]
            target = row[target_col]
            
            # Add to forward adjacency
            self.adjacency_list[source].add(target)
            
            # Add to reverse adjacency
            self.reverse_adjacency[target].add(source)
            
            # Store edge weight if available
            if self.has_weights:
                weight = float(row[weight_col])
                self.edge_weights[(source, target)] = weight
                if not directed:
                    self.edge_weights[(target, source)] = weight
            
            # If undirected, add reverse edge
            if not directed:
                self.adjacency_list[target].add(source)
                self.reverse_adjacency[source].add(target)
        
        # Calculate node degrees
        self.node_count = len(set(df[source_col].unique()) | set(df[target_col].unique()))
        self.edge_count = len(df)
        
        for node in self.adjacency_list:
            self.node_degrees[node] = len(self.adjacency_list[node])
        
        weight_info = " (with weights)" if self.has_weights else ""
        print(f"Indexed {self.node_count} nodes and {self.edge_count} edges{weight_info}")
    
    def get_neighbors(self, node: int, direction: str = 'out') -> Set[int]:
        """
        Get neighbors of a node.
        
        Args:
            node: Node ID
            direction: 'out' for outgoing neighbors, 'in' for incoming, 'both' for both
        
        Returns:
            Set of neighbor node IDs
        """
        neighbors = set()
        
        if direction in ['out', 'both']:
            neighbors.update(self.adjacency_list.get(node, set()))
        
        if direction in ['in', 'both']:
            neighbors.update(self.reverse_adjacency.get(node, set()))
        
        return neighbors
    
    def get_degree(self, node: int) -> int:
        """
        Get degree of a node (number of neighbors).
        
        Args:
            node: Node ID
        
        Returns:
            Degree of the node
        """
        return self.node_degrees.get(node, 0)
    
    def has_node(self, node: int) -> bool:
        """
        Check if a node exists in the graph.
        
        Args:
            node: Node ID
        
        Returns:
            True if node exists, False otherwise
        """
        return node in self.adjacency_list or node in self.reverse_adjacency
    
    def has_edge(self, source: int, target: int) -> bool:
        """
        Check if an edge exists between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
        
        Returns:
            True if edge exists, False otherwise
        """
        return target in self.adjacency_list.get(source, set())
    
    def get_edge_weight(self, source: int, target: int, default: float = 1.0) -> float:
        """
        Get weight of an edge.
        
        Args:
            source: Source node ID
            target: Target node ID
            default: Default weight if edge has no weight or doesn't exist
        
        Returns:
            Edge weight or default value
        """
        return self.edge_weights.get((source, target), default)
    
    def get_all_nodes(self) -> Set[int]:
        """
        Get all nodes in the graph.
        
        Returns:
            Set of all node IDs
        """
        return set(self.adjacency_list.keys()) | set(self.reverse_adjacency.keys())
    
    def get_statistics(self) -> Dict:
        """
        Get graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        degrees = list(self.node_degrees.values())
        
        return {
            'node_count': self.node_count,
            'edge_count': self.edge_count,
            'avg_degree': np.mean(degrees) if degrees else 0,
            'max_degree': max(degrees) if degrees else 0,
            'min_degree': min(degrees) if degrees else 0
        }
    
    def save(self, file_path: str):
        """
        Save indexes to disk.
        
        Args:
            file_path: Path to save the index file
        """
        # Convert sets to lists for pickle compatibility
        index_data = {
            'adjacency_list': {k: list(v) for k, v in self.adjacency_list.items()},
            'reverse_adjacency': {k: list(v) for k, v in self.reverse_adjacency.items()},
            'edge_weights': self.edge_weights,
            'has_weights': self.has_weights,
            'node_degrees': self.node_degrees,
            'edge_count': self.edge_count,
            'node_count': self.node_count
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"Saved index to {file_path}")
    
    def load(self, file_path: str):
        """
        Load indexes from disk.
        
        Args:
            file_path: Path to the index file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Index file not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            index_data = pickle.load(f)
        
        # Convert lists back to sets
        self.adjacency_list = {k: set(v) for k, v in index_data['adjacency_list'].items()}
        self.reverse_adjacency = {k: set(v) for k, v in index_data['reverse_adjacency'].items()}
        self.edge_weights = index_data.get('edge_weights', {})
        self.has_weights = index_data.get('has_weights', False)
        self.node_degrees = index_data['node_degrees']
        self.edge_count = index_data['edge_count']
        self.node_count = index_data['node_count']
        
        print(f"Loaded index from {file_path}")

