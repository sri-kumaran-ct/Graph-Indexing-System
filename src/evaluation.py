"""
Evaluation Module
Measures query latency, memory usage, and throughput.
"""

import time
import psutil
import os
from typing import Dict, List, Optional
from contextlib import contextmanager
from src.query_engine import QueryEngine
from src.indexing import GraphIndex


class PerformanceMetrics:
    """
    Collects and reports performance metrics for graph operations.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            'query_latencies': [],
            'memory_usage': [],
            'query_count': 0,
            'total_time': 0.0
        }
        self.process = psutil.Process(os.getpid())
    
    def get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in megabytes
        """
        return self.process.memory_info().rss / 1024 / 1024
    
    @contextmanager
    def measure_query(self):
        """
        Context manager to measure query execution time and memory.
        
        Usage:
            with metrics.measure_query():
                result = query_engine.lookup_node(node_id)
        """
        start_time = time.time()
        start_memory = self.get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.get_memory_usage()
            
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            memory_delta = end_memory - start_memory
            
            self.metrics['query_latencies'].append(latency)
            self.metrics['memory_usage'].append(end_memory)
            self.metrics['query_count'] += 1
            self.metrics['total_time'] += latency / 1000  # Keep in seconds
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.metrics['query_latencies']:
            return {
                'query_count': 0,
                'message': 'No queries executed yet'
            }
        
        latencies = self.metrics['query_latencies']
        memory_values = self.metrics['memory_usage']
        
        return {
            'query_count': self.metrics['query_count'],
            'total_time_seconds': self.metrics['total_time'],
            'throughput_qps': self.metrics['query_count'] / self.metrics['total_time'] if self.metrics['total_time'] > 0 else 0,
            'latency_ms': {
                'mean': sum(latencies) / len(latencies),
                'median': sorted(latencies)[len(latencies) // 2],
                'min': min(latencies),
                'max': max(latencies),
                'p95': sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 0 else 0,
                'p99': sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 0 else 0
            },
            'memory_mb': {
                'current': memory_values[-1] if memory_values else 0,
                'mean': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max': max(memory_values) if memory_values else 0,
                'min': min(memory_values) if memory_values else 0
            }
        }
    
    def reset(self):
        """Reset all metrics."""
        self.metrics = {
            'query_latencies': [],
            'memory_usage': [],
            'query_count': 0,
            'total_time': 0.0
        }
    
    def print_report(self):
        """Print a formatted performance report."""
        stats = self.get_statistics()
        
        if stats.get('query_count', 0) == 0:
            print("No performance data available.")
            return
        
        print("\n" + "="*60)
        print("PERFORMANCE REPORT")
        print("="*60)
        print(f"Total Queries: {stats['query_count']}")
        print(f"Total Time: {stats['total_time_seconds']:.2f} seconds")
        print(f"Throughput: {stats['throughput_qps']:.2f} queries/second")
        print("\nLatency (ms):")
        print(f"  Mean:   {stats['latency_ms']['mean']:.2f}")
        print(f"  Median: {stats['latency_ms']['median']:.2f}")
        print(f"  Min:    {stats['latency_ms']['min']:.2f}")
        print(f"  Max:    {stats['latency_ms']['max']:.2f}")
        print(f"  P95:    {stats['latency_ms']['p95']:.2f}")
        print(f"  P99:    {stats['latency_ms']['p99']:.2f}")
        print("\nMemory (MB):")
        print(f"  Current: {stats['memory_mb']['current']:.2f}")
        print(f"  Mean:    {stats['memory_mb']['mean']:.2f}")
        print(f"  Max:     {stats['memory_mb']['max']:.2f}")
        print(f"  Min:     {stats['memory_mb']['min']:.2f}")
        print("="*60 + "\n")


class BenchmarkSuite:
    """
    Benchmark suite for evaluating graph database performance.
    """
    
    def __init__(self, query_engine: QueryEngine, graph_index: GraphIndex):
        """
        Initialize benchmark suite.
        
        Args:
            query_engine: QueryEngine instance
            graph_index: GraphIndex instance
        """
        self.query_engine = query_engine
        self.graph_index = graph_index
        self.metrics = PerformanceMetrics()
    
    def benchmark_node_lookup(self, num_queries: int = 100) -> Dict:
        """
        Benchmark node lookup queries.
        
        Args:
            num_queries: Number of queries to execute
        
        Returns:
            Performance statistics
        """
        print(f"Benchmarking node lookup ({num_queries} queries)...")
        
        all_nodes = list(self.graph_index.get_all_nodes())
        if not all_nodes:
            return {'error': 'No nodes in graph'}
        
        import random
        random.seed(42)  # For reproducibility
        
        self.metrics.reset()
        
        for _ in range(num_queries):
            node_id = random.choice(all_nodes)
            with self.metrics.measure_query():
                self.query_engine.lookup_node(node_id)
        
        return self.metrics.get_statistics()
    
    def benchmark_neighbor_query(self, num_queries: int = 100) -> Dict:
        """
        Benchmark neighbor queries.
        
        Args:
            num_queries: Number of queries to execute
        
        Returns:
            Performance statistics
        """
        print(f"Benchmarking neighbor queries ({num_queries} queries)...")
        
        all_nodes = list(self.graph_index.get_all_nodes())
        if not all_nodes:
            return {'error': 'No nodes in graph'}
        
        import random
        random.seed(42)
        
        self.metrics.reset()
        
        for _ in range(num_queries):
            node_id = random.choice(all_nodes)
            with self.metrics.measure_query():
                self.query_engine.get_neighbors(node_id)
        
        return self.metrics.get_statistics()
    
    def benchmark_path_query(self, num_queries: int = 50) -> Dict:
        """
        Benchmark path finding queries.
        
        Args:
            num_queries: Number of queries to execute
        
        Returns:
            Performance statistics
        """
        print(f"Benchmarking path queries ({num_queries} queries)...")
        
        all_nodes = list(self.graph_index.get_all_nodes())
        if len(all_nodes) < 2:
            return {'error': 'Not enough nodes for path queries'}
        
        import random
        random.seed(42)
        
        self.metrics.reset()
        
        for _ in range(num_queries):
            source, target = random.sample(all_nodes, 2)
            with self.metrics.measure_query():
                self.query_engine.find_path(source, target, max_depth=5)
        
        return self.metrics.get_statistics()
    
    def run_full_benchmark(self) -> Dict:
        """
        Run complete benchmark suite.
        
        Returns:
            Dictionary with all benchmark results
        """
        print("\n" + "="*60)
        print("RUNNING FULL BENCHMARK SUITE")
        print("="*60 + "\n")
        
        results = {
            'node_lookup': self.benchmark_node_lookup(100),
            'neighbor_query': self.benchmark_neighbor_query(100),
            'path_query': self.benchmark_path_query(50)
        }
        
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        
        for test_name, stats in results.items():
            if 'error' not in stats:
                print(f"\n{test_name.upper()}:")
                print(f"  Throughput: {stats['throughput_qps']:.2f} qps")
                print(f"  Mean Latency: {stats['latency_ms']['mean']:.2f} ms")
        
        print("="*60 + "\n")
        
        return results

