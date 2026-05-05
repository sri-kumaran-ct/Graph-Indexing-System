"""
Main Entry Point
Command-line interface for the graph database system.
"""

import argparse
import json
import sys
from src.graph_database import GraphDatabase
from src.security import Permission
from src.evaluation import BenchmarkSuite, PerformanceMetrics


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Graph Database System - Efficient indexing and querying of massive graphs'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Load and index command
    load_parser = subparsers.add_parser('load', help='Load and index a graph from file')
    load_parser.add_argument('file_path', help='Path to graph data file (CSV/edge list)')
    load_parser.add_argument('--source-col', default='source', help='Source column name')
    load_parser.add_argument('--target-col', default='target', help='Target column name')
    load_parser.add_argument('--weight-col', help='Weight column name (optional)')
    load_parser.add_argument('--delimiter', default=',', help='File delimiter')
    load_parser.add_argument('--no-dask', action='store_true', help='Disable Dask processing')
    load_parser.add_argument('--no-normalize', action='store_true', help='Disable node ID normalization')
    load_parser.add_argument('--no-clean', action='store_true', help='Disable data cleaning')
    load_parser.add_argument('--undirected', action='store_true', help='Treat graph as undirected')
    load_parser.add_argument('--output-index', help='Path to save index file')
    load_parser.add_argument('--no-security', action='store_true', help='Disable security features')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Execute a query')
    query_parser.add_argument('query_type', choices=['lookup', 'neighbors', 'path', 'common_neighbors', 'stats'],
                             help='Type of query to execute')
    query_parser.add_argument('--user-id', default='default_user', help='User ID for access control')
    query_parser.add_argument('--node-id', type=int, help='Node ID for lookup/neighbors/stats queries')
    query_parser.add_argument('--source', type=int, help='Source node for path query')
    query_parser.add_argument('--target', type=int, help='Target node for path query')
    query_parser.add_argument('--node1', type=int, help='First node for common_neighbors query')
    query_parser.add_argument('--node2', type=int, help='Second node for common_neighbors query')
    query_parser.add_argument('--direction', choices=['in', 'out', 'both'], default='out',
                             help='Direction for neighbor queries')
    query_parser.add_argument('--max-depth', type=int, default=10, help='Max depth for path queries')
    query_parser.add_argument('--limit', type=int, help='Limit number of results')
    query_parser.add_argument('--index-file', help='Path to load index from')
    query_parser.add_argument('--no-security', action='store_true', help='Disable security features')
    
    # Security command
    security_parser = subparsers.add_parser('security', help='Manage security settings')
    security_parser.add_argument('action', choices=['add-user', 'remove-user', 'block-node', 'unblock-node',
                                                    'set-rate-limit', 'user-stats'],
                                 help='Security action to perform')
    security_parser.add_argument('--user-id', help='User ID')
    security_parser.add_argument('--permission', choices=['read_only', 'read_write', 'admin'],
                                default='read_only', help='Permission level')
    security_parser.add_argument('--node-id', type=int, help='Node ID')
    security_parser.add_argument('--max-queries', type=int, help='Max queries for rate limit')
    security_parser.add_argument('--window-seconds', type=int, default=60, help='Time window for rate limit')
    security_parser.add_argument('--index-file', help='Path to load index from')
    security_parser.add_argument('--no-security', action='store_true', help='Disable security features')
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Run performance benchmarks')
    benchmark_parser.add_argument('--index-file', required=True, help='Path to index file')
    benchmark_parser.add_argument('--test', choices=['all', 'lookup', 'neighbors', 'path'],
                                default='all', help='Which tests to run')
    benchmark_parser.add_argument('--num-queries', type=int, default=100, help='Number of queries per test')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Get graph statistics')
    stats_parser.add_argument('--index-file', help='Path to load index from')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize database
    enable_security = not args.no_security if hasattr(args, 'no_security') else True
    db = GraphDatabase(enable_security=enable_security)
    
    # Handle commands
    if args.command == 'load':
        result = db.load_and_index(
            args.file_path,
            source_col=args.source_col,
            target_col=args.target_col,
            weight_col=args.weight_col,
            delimiter=args.delimiter,
            normalize=not args.no_normalize,
            clean=not args.no_clean,
            directed=not args.undirected,
            use_dask=not args.no_dask
        )
        
        if args.output_index:
            db.save_index(args.output_index)
            print(f"Index saved to {args.output_index}")
        
        print("\nGraph loaded and indexed successfully!")
        print(f"Statistics: {json.dumps(result['statistics'], indent=2)}")
    
    elif args.command == 'query':
        # Load index if provided
        if args.index_file:
            db.load_index(args.index_file)
        elif not db.is_indexed:
            print("Error: Graph not indexed. Use 'load' command first or provide --index-file")
            sys.exit(1)
        
        # Build query kwargs
        query_kwargs = {}
        if args.node_id is not None:
            query_kwargs['node_id'] = args.node_id
        if args.source is not None:
            query_kwargs['source'] = args.source
        if args.target is not None:
            query_kwargs['target'] = args.target
        if args.node1 is not None:
            query_kwargs['node1'] = args.node1
        if args.node2 is not None:
            query_kwargs['node2'] = args.node2
        if args.direction:
            query_kwargs['direction'] = args.direction
        if args.max_depth:
            query_kwargs['max_depth'] = args.max_depth
        if args.limit:
            query_kwargs['limit'] = args.limit
        
        result = db.query(args.user_id, args.query_type, **query_kwargs)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'security':
        if not db.access_control:
            print("Error: Security is disabled")
            sys.exit(1)
        
        # Load index if provided
        if args.index_file:
            db.load_index(args.index_file)
        
        if args.action == 'add-user':
            permission = Permission[args.permission.upper()]
            db.access_control.add_user(args.user_id, permission)
            print(f"User {args.user_id} added with {args.permission} permission")
        
        elif args.action == 'remove-user':
            db.access_control.remove_user(args.user_id)
            print(f"User {args.user_id} removed")
        
        elif args.action == 'block-node':
            db.access_control.block_node(args.node_id)
            print(f"Node {args.node_id} blocked")
        
        elif args.action == 'unblock-node':
            db.access_control.unblock_node(args.node_id)
            print(f"Node {args.node_id} unblocked")
        
        elif args.action == 'set-rate-limit':
            db.access_control.set_rate_limit(args.user_id, args.max_queries, args.window_seconds)
            print(f"Rate limit set for {args.user_id}: {args.max_queries} queries per {args.window_seconds} seconds")
        
        elif args.action == 'user-stats':
            stats = db.access_control.get_user_stats(args.user_id)
            print(json.dumps(stats, indent=2))
    
    elif args.command == 'benchmark':
        db.load_index(args.index_file)
        
        benchmark = BenchmarkSuite(db.query_engine, db.index)
        
        if args.test == 'all':
            benchmark.run_full_benchmark()
        elif args.test == 'lookup':
            result = benchmark.benchmark_node_lookup(args.num_queries)
            print(json.dumps(result, indent=2))
        elif args.test == 'neighbors':
            result = benchmark.benchmark_neighbor_query(args.num_queries)
            print(json.dumps(result, indent=2))
        elif args.test == 'path':
            result = benchmark.benchmark_path_query(args.num_queries)
            print(json.dumps(result, indent=2))
    
    elif args.command == 'stats':
        if args.index_file:
            db.load_index(args.index_file)
        elif not db.is_indexed:
            print("Error: Graph not indexed. Use 'load' command first or provide --index-file")
            sys.exit(1)
        
        stats = db.get_graph_statistics()
        print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()

