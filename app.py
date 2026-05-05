"""
Flask Web Application
Minimal web interface for the Graph Database System.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
from src.graph_database import GraphDatabase
from src.security import Permission
from src.evaluation import BenchmarkSuite, PerformanceMetrics

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Global database instance
db = GraphDatabase(enable_security=True)
db_initialized = False

# Automatically add web_user for web interface
db.access_control.add_user('web_user', Permission.READ_ONLY)

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/status')
def status():
    """Get system status."""
    return jsonify({
        'initialized': db_initialized,
        'statistics': db.get_graph_statistics() if db_initialized else None
    })


@app.route('/api/load', methods=['POST'])
def load_graph():
    """Load and index a graph from uploaded file."""
    global db_initialized
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        upload_path = os.path.join('data', 'uploaded_graph.csv')
        os.makedirs('data', exist_ok=True)
        file.save(upload_path)
        
        # Get parameters
        source_col = request.form.get('source_col', 'source')
        target_col = request.form.get('target_col', 'target')
        weight_col = request.form.get('weight_col', 'weight')  # Default to 'weight'
        normalize = request.form.get('normalize', 'true').lower() == 'true'
        clean = request.form.get('clean', 'true').lower() == 'true'
        directed = request.form.get('directed', 'true').lower() == 'true'
        use_dask = request.form.get('use_dask', 'true').lower() == 'true'
        
        # Load and index
        result = db.load_and_index(
            upload_path,
            source_col=source_col,
            target_col=target_col,
            weight_col=weight_col if weight_col else None,  # Pass None if empty string
            normalize=normalize,
            clean=clean,
            directed=directed,
            use_dask=use_dask
        )
        
        # Save index
        index_path = os.path.join('data', 'graph_index.pkl')
        db.save_index(index_path)
        
        db_initialized = True
        
        return jsonify({
            'success': True,
            'message': 'Graph loaded and indexed successfully',
            'statistics': result['statistics']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/load_index', methods=['POST'])
def load_index():
    """Load index from file."""
    global db_initialized
    
    try:
        data = request.get_json()
        index_path = data.get('index_path', 'data/graph_index.pkl')
        
        if not os.path.exists(index_path):
            return jsonify({'error': f'Index file not found: {index_path}'}), 404
        
        db.load_index(index_path)
        db_initialized = True
        
        stats = db.get_graph_statistics()
        return jsonify({
            'success': True,
            'message': 'Index loaded successfully',
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query', methods=['POST'])
def query():
    """Execute a graph query."""
    if not db_initialized:
        return jsonify({'error': 'Graph not loaded. Please load a graph first.'}), 400
    
    try:
        data = request.get_json()
        query_type = data.get('query_type')
        user_id = data.get('user_id', 'web_user')
        
        # Build query parameters
        query_params = {}
        
        if query_type == 'lookup':
            query_params['node_id'] = int(data.get('node_id'))
        elif query_type == 'neighbors':
            query_params['node_id'] = int(data.get('node_id'))
            query_params['direction'] = data.get('direction', 'out')
            if 'limit' in data:
                query_params['limit'] = int(data.get('limit'))
        elif query_type == 'path':
            query_params['source'] = int(data.get('source'))
            query_params['target'] = int(data.get('target'))
            query_params['max_depth'] = int(data.get('max_depth', 10))
            query_params['directed'] = data.get('directed', True)
            query_params['use_weights'] = data.get('use_weights', True)
        elif query_type == 'common_neighbors':
            query_params['node1'] = int(data.get('node1'))
            query_params['node2'] = int(data.get('node2'))
            query_params['direction'] = data.get('direction', 'out')
        elif query_type == 'stats':
            query_params['node_id'] = int(data.get('node_id'))
        else:
            return jsonify({'error': f'Unknown query type: {query_type}'}), 400
        
        result = db.query(user_id, query_type, **query_params)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/security/add_user', methods=['POST'])
def add_user():
    """Add a user to the access control system."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        permission_str = data.get('permission', 'read_only').upper()
        
        permission = Permission[permission_str]
        db.access_control.add_user(user_id, permission)
        
        return jsonify({
            'success': True,
            'message': f'User {user_id} added with {permission_str} permission'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/security/block_node', methods=['POST'])
def block_node():
    """Block access to a node."""
    try:
        data = request.get_json()
        node_id = int(data.get('node_id'))
        
        db.access_control.block_node(node_id)
        
        return jsonify({
            'success': True,
            'message': f'Node {node_id} blocked'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/benchmark', methods=['POST'])
def benchmark():
    """Run performance benchmarks."""
    if not db_initialized:
        return jsonify({'error': 'Graph not loaded. Please load a graph first.'}), 400
    
    try:
        data = request.get_json() or {}
        test_type = data.get('test', 'all')
        num_queries = int(data.get('num_queries', 100))
        
        benchmark_suite = BenchmarkSuite(db.query_engine, db.index)
        
        if test_type == 'all':
            results = benchmark_suite.run_full_benchmark()
        elif test_type == 'lookup':
            results = benchmark_suite.benchmark_node_lookup(num_queries)
        elif test_type == 'neighbors':
            results = benchmark_suite.benchmark_neighbor_query(num_queries)
        elif test_type == 'path':
            results = benchmark_suite.benchmark_path_query(num_queries)
        else:
            return jsonify({'error': f'Unknown test type: {test_type}'}), 400
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics')
def statistics():
    """Get graph statistics."""
    if not db_initialized:
        return jsonify({'error': 'Graph not loaded'}), 400
    
    try:
        stats = db.get_graph_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("\n" + "="*60)
    print("Graph Database System - Web Interface")
    print("="*60)
    print("Starting Flask server...")
    print("Open your browser to: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
