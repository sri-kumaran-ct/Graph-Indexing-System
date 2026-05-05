"""
Example script demonstrating the Graph Database System usage.
"""

from src.graph_database import GraphDatabase
from src.security import Permission
from src.evaluation import BenchmarkSuite

def main():
    """Run example usage of the graph database."""
    
    print("="*60)
    print("Graph Database System - Example Usage")
    print("="*60 + "\n")
    
    # Initialize database with security enabled
    print("1. Initializing database...")
    db = GraphDatabase(enable_security=True)
    
    # Load and index a sample graph
    print("\n2. Loading and indexing graph...")
    try:
        result = db.load_and_index(
            'data/sample_graph.csv',
            source_col='source',
            target_col='target',
            normalize=True,
            clean=True,
            directed=True
        )
        print(f"   Graph loaded: {result['statistics']}")
    except FileNotFoundError:
        print("   Error: sample_graph.csv not found. Please create it first.")
        return
    
    # Save index for later use
    print("\n3. Saving index...")
    db.save_index('data/sample_graph_index.pkl')
    print("   Index saved to data/sample_graph_index.pkl")
    
    # Set up security
    print("\n4. Setting up security...")
    db.access_control.add_user('alice', Permission.READ_ONLY)
    db.access_control.add_user('bob', Permission.READ_WRITE)
    db.access_control.set_rate_limit('alice', max_queries=100, window_seconds=60)
    print("   Users added: alice (read_only), bob (read_write)")
    
    # Example queries
    print("\n5. Running example queries...")
    
    # Node lookup
    print("\n   Query 1: Node lookup (node 0)")
    result = db.query('alice', 'lookup', node_id=0)
    print(f"   Result: {result}")
    
    # Get neighbors
    print("\n   Query 2: Get neighbors of node 0")
    result = db.query('alice', 'neighbors', node_id=0, direction='out')
    print(f"   Result: {result}")
    
    # Find path
    print("\n   Query 3: Find path from node 0 to node 5")
    result = db.query('bob', 'path', source=0, target=5, max_depth=10)
    print(f"   Result: {result}")
    
    # Common neighbors
    print("\n   Query 4: Common neighbors of nodes 1 and 2")
    result = db.query('alice', 'common_neighbors', node1=1, node2=2)
    print(f"   Result: {result}")
    
    # Get statistics
    print("\n6. Graph statistics:")
    stats = db.get_graph_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Run benchmarks
    print("\n7. Running performance benchmarks...")
    benchmark = BenchmarkSuite(db.query_engine, db.index)
    benchmark_results = benchmark.run_full_benchmark()
    
    print("\n" + "="*60)
    print("Example completed successfully!")
    print("="*60)

if __name__ == '__main__':
    main()

