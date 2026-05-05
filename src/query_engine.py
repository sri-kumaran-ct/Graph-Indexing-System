"""
Query Engine Module
Supports basic graph queries: node lookup, neighbor query, and simple path queries.
"""

from typing import List, Optional, Set, Tuple
from collections import deque
import time
from src.indexing import GraphIndex


class QueryEngine:
    """
    Query engine for graph database operations.
    Supports node lookup, neighbor queries, and path finding.
    """
    
    def __init__(self, graph_index: GraphIndex):
        """
        Initialize query engine with a graph index.
        
        Args:
            graph_index: GraphIndex instance containing the graph data
        """
        self.index = graph_index
    
    def lookup_node(self, node_id: int) -> dict:
        """
        Lookup information about a specific node.
        
        Args:
            node_id: Node ID to lookup
        
        Returns:
            Dictionary with node information (existence, degree, neighbors count)
        """
        exists = self.index.has_node(node_id)
        
        if not exists:
            return {
                'node_id': node_id,
                'exists': False,
                'message': f'Node {node_id} not found in graph'
            }
        
        out_degree = len(self.index.get_neighbors(node_id, direction='out'))
        in_degree = len(self.index.get_neighbors(node_id, direction='in'))
        total_degree = len(self.index.get_neighbors(node_id, direction='both'))
        
        return {
            'node_id': int(node_id),
            'exists': True,
            'out_degree': int(out_degree),
            'in_degree': int(in_degree),
            'total_degree': int(total_degree)
        }
    
    def get_neighbors(self, node_id: int, 
                     direction: str = 'out',
                     limit: Optional[int] = None) -> dict:
        """
        Get neighbors of a node.
        
        Args:
            node_id: Node ID
            direction: 'out' for outgoing, 'in' for incoming, 'both' for both
            limit: Optional limit on number of neighbors to return
        
        Returns:
            Dictionary with neighbor information
        """
        if not self.index.has_node(node_id):
            return {
                'node_id': node_id,
                'exists': False,
                'neighbors': [],
                'count': 0
            }
        
        neighbors = self.index.get_neighbors(node_id, direction=direction)
        neighbor_list = [int(n) for n in neighbors]
        
        if limit is not None:
            neighbor_list = neighbor_list[:limit]
        
        # Include weights if available
        neighbors_with_weights = None
        if self.index.has_weights:
            neighbors_with_weights = {}
            for neighbor in neighbor_list:
                weight = self.index.get_edge_weight(node_id, neighbor, 1.0)
                neighbors_with_weights[neighbor] = weight
        
        result = {
            'node_id': int(node_id),
            'exists': True,
            'direction': direction,
            'neighbors': neighbor_list,
            'count': len(neighbor_list),
            'total_count': len(neighbors)
        }
        
        if neighbors_with_weights:
            result['neighbors_with_weights'] = neighbors_with_weights
            result['has_weights'] = True
        
        return result
    
    def find_path(self, source: int, target: int, 
                  max_depth: int = 10,
                  directed: bool = True,
                  use_weights: bool = True) -> dict:
        """
        Find a simple path between two nodes using BFS.
        
        Args:
            source: Source node ID
            target: Target node ID
            max_depth: Maximum path length to search
            directed: Whether to respect edge direction
        
        Returns:
            Dictionary with path information
        """
        if not self.index.has_node(source):
            return {
                'source': source,
                'target': target,
                'path_exists': False,
                'message': f'Source node {source} not found'
            }
        
        if not self.index.has_node(target):
            return {
                'source': source,
                'target': target,
                'path_exists': False,
                'message': f'Target node {target} not found'
            }
        
        if source == target:
            return {
                'source': int(source),
                'target': int(target),
                'path_exists': True,
                'path': [int(source)],
                'length': 0,
                'total_weight': 0.0
            }
        
        # Use weighted shortest path (Dijkstra) if weights are available and requested
        if use_weights and self.index.has_weights:
            return self._find_weighted_path(source, target, max_depth, directed)
        
        # Otherwise use BFS for unweighted shortest path
        queue = deque([(source, [source], 0.0)])
        visited = {source}
        
        while queue:
            current, path, total_weight = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            # Get neighbors based on direction
            if directed:
                neighbors = self.index.get_neighbors(current, direction='out')
            else:
                neighbors = self.index.get_neighbors(current, direction='both')
            
            for neighbor in neighbors:
                if neighbor == target:
                    full_path = path + [neighbor]
                    edge_weight = self.index.get_edge_weight(current, neighbor, 1.0)
                    return {
                        'source': int(source),
                        'target': int(target),
                        'path_exists': True,
                        'path': [int(n) for n in full_path],
                        'length': len(full_path) - 1,
                        'total_weight': total_weight + edge_weight
                    }
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    edge_weight = self.index.get_edge_weight(current, neighbor, 1.0)
                    queue.append((neighbor, path + [neighbor], total_weight + edge_weight))
        
        return {
            'source': int(source),
            'target': int(target),
            'path_exists': False,
            'message': f'No path found within depth {max_depth}'
        }
    
    def _find_weighted_path(self, source: int, target: int, 
                           max_depth: int, directed: bool) -> dict:
        """
        Find shortest weighted path using Dijkstra's algorithm.
        
        Args:
            source: Source node ID
            target: Target node ID
            max_depth: Maximum path length
            directed: Whether graph is directed
        
        Returns:
            Dictionary with path information including total weight
        """
        import heapq
        
        # Priority queue: (total_weight, current_node, path)
        pq = [(0.0, source, [source])]
        distances = {source: 0.0}
        visited = set()
        
        while pq:
            total_weight, current, path = heapq.heappop(pq)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            if len(path) > max_depth:
                continue
            
            if current == target:
                return {
                    'source': int(source),
                    'target': int(target),
                    'path_exists': True,
                    'path': [int(n) for n in path],
                    'length': len(path) - 1,
                    'total_weight': total_weight
                }
            
            # Get neighbors
            if directed:
                neighbors = self.index.get_neighbors(current, direction='out')
            else:
                neighbors = self.index.get_neighbors(current, direction='both')
            
            for neighbor in neighbors:
                if neighbor in visited:
                    continue
                
                edge_weight = self.index.get_edge_weight(current, neighbor, 1.0)
                new_weight = total_weight + edge_weight
                
                # Only consider if this is a shorter path
                if neighbor not in distances or new_weight < distances[neighbor]:
                    distances[neighbor] = new_weight
                    heapq.heappush(pq, (new_weight, neighbor, path + [neighbor]))
        
        return {
            'source': int(source),
            'target': int(target),
            'path_exists': False,
            'message': f'No path found within depth {max_depth}'
        }
    
    def get_common_neighbors(self, node1: int, node2: int,
                            direction: str = 'out') -> dict:
        """
        Find common neighbors between two nodes.
        
        Args:
            node1: First node ID
            node2: Second node ID
            direction: Direction for neighbor lookup
        
        Returns:
            Dictionary with common neighbors information
        """
        if not self.index.has_node(node1) or not self.index.has_node(node2):
            return {
                'node1': node1,
                'node2': node2,
                'common_neighbors': [],
                'count': 0,
                'message': 'One or both nodes not found'
            }
        
        neighbors1 = self.index.get_neighbors(node1, direction=direction)
        neighbors2 = self.index.get_neighbors(node2, direction=direction)
        
        common = neighbors1 & neighbors2
        
        return {
            'node1': int(node1),
            'node2': int(node2),
            'common_neighbors': [int(n) for n in list(common)],
            'count': len(common)
        }
    
    def get_node_statistics(self, node_id: int) -> dict:
        """
        Get comprehensive statistics for a node.
        
        Args:
            node_id: Node ID
        
        Returns:
            Dictionary with node statistics
        """
        lookup_result = self.lookup_node(node_id)
        
        if not lookup_result['exists']:
            return lookup_result
        
        out_neighbors = self.index.get_neighbors(node_id, direction='out')
        in_neighbors = self.index.get_neighbors(node_id, direction='in')
        
        return {
            'node_id': int(node_id),
            'exists': True,
            'out_degree': len(out_neighbors),
            'in_degree': len(in_neighbors),
            'total_degree': len(out_neighbors | in_neighbors),
            'out_neighbors_sample': [int(n) for n in list(out_neighbors)[:10]],  # Sample of neighbors
            'in_neighbors_sample': [int(n) for n in list(in_neighbors)[:10]]
        }

