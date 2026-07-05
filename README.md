# Graph Database System

A prototype system for efficient indexing and querying of massive graph databases. Built with Python, focusing on practicality, scalability, and reproducibility.

## Features:

- **Graph Data Loading**: Load graphs from CSV files and edge lists.
- **Efficient Preprocessing**: Use Dask for handling large datasets.
- **Fast Indexing**: Lightweight indexes for rapid node and neighbor lookups.
- **Query Engine**: Support for node lookup, neighbor queries, and path finding.
- **Security**: Basic access control and query restrictions.
- **Performance Evaluation**: Built-in benchmarking and metrics collection.

## Architecture

```
┌─────────────────┐
│  Data Sources   │ (CSV, Edge Lists)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Loader    │ (Dask-based loading)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Preprocessor   │ (Cleaning, Normalization)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Indexer     │ (Adjacency lists, degrees)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query Engine   │ (Lookup, Neighbors, Paths)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Security      │ (Access control, Rate limiting)
└─────────────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Setup

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Option 1: Web Interface (Recommended)

1. **Start the Flask web server:**
   ```bash
   python app.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:5000`

3. **Use the web interface:**
   - Upload a graph file (CSV/edge list)
   - Execute queries through the interactive UI
   - View statistics and run benchmarks

### Option 2: Command Line Interface

### 1. Prepare Graph Data

Create a CSV file with graph edges. Example `graph.csv`:
```csv
source,target
0,1
0,2
1,2
1,3
2,3
```

### 2. Load and Index Graph

```bash
python main.py load graph.csv --output-index graph_index.pkl
```

### 3. Query the Graph

**Node Lookup:**
```bash
python main.py query lookup --node-id 0 --index-file graph_index.pkl
```

**Get Neighbors:**
```bash
python main.py query neighbors --node-id 0 --index-file graph_index.pkl
```

**Find Path:**
```bash
python main.py query path --source 0 --target 3 --index-file graph_index.pkl
```

**Common Neighbors:**
```bash
python main.py query common_neighbors --node1 0 --node2 1 --index-file graph_index.pkl
```

### 4. Run Benchmarks

```bash
python main.py benchmark --index-file graph_index.pkl
```

## Usage Examples

### Loading Large Graphs

For large graphs, the system automatically uses Dask for efficient processing:

```bash
python main.py load large_graph.csv \
    --source-col from_node \
    --target-col to_node \
    --output-index large_graph_index.pkl
```

### Security Features

**Add a user:**
```bash
python main.py security add-user --user-id alice --permission read_only
```

**Block a node:**
```bash
python main.py security block-node --node-id 42
```

**Set rate limit:**
```bash
python main.py security set-rate-limit --user-id alice --max-queries 100 --window-seconds 60
```

**Query with user authentication:**
```bash
python main.py query lookup --user-id alice --node-id 0 --index-file graph_index.pkl
```

### Graph Statistics

```bash
python main.py stats --index-file graph_index.pkl
```

## Command Reference

### Load Command
```bash
python main.py load <file_path> [options]

Options:
  --source-col COL        Source column name (default: source)
  --target-col COL        Target column name (default: target)
  --weight-col COL        Weight column name (optional)
  --delimiter DELIM       File delimiter (default: ,)
  --no-dask               Disable Dask processing
  --no-normalize           Disable node ID normalization
  --no-clean               Disable data cleaning
  --undirected            Treat graph as undirected
  --output-index PATH     Save index to file
  --no-security            Disable security features
```

### Query Command
```bash
python main.py query <query_type> [options]

Query Types:
  lookup              Node lookup
  neighbors           Get neighbors
  path                Find path between nodes
  common_neighbors    Find common neighbors
  stats               Node statistics

Options:
  --user-id ID        User ID for access control
  --node-id ID        Node ID
  --source ID         Source node (for path query)
  --target ID         Target node (for path query)
  --node1 ID          First node (for common_neighbors)
  --node2 ID          Second node (for common_neighbors)
  --direction DIR     Direction: in, out, both (default: out)
  --max-depth N       Max depth for path queries (default: 10)
  --limit N           Limit number of results
  --index-file PATH   Load index from file
```

### Security Command
```bash
python main.py security <action> [options]

Actions:
  add-user            Add a new user
  remove-user         Remove a user
  block-node          Block access to a node
  unblock-node        Unblock access to a node
  set-rate-limit      Set rate limit for user
  user-stats          Get user statistics
```

### Benchmark Command
```bash
python main.py benchmark --index-file <path> [options]

Options:
  --test TEST         Test to run: all, lookup, neighbors, path
  --num-queries N     Number of queries per test (default: 100)
```

## Python API

You can also use the system programmatically:

```python
from src.graph_database import GraphDatabase
from src.security import Permission

# Initialize database
db = GraphDatabase(enable_security=True)

# Load and index graph
db.load_and_index('graph.csv', output_index='graph_index.pkl')

# Add users
db.access_control.add_user('alice', Permission.READ_ONLY)
db.access_control.add_user('bob', Permission.READ_WRITE)

# Execute queries
result = db.query('alice', 'lookup', node_id=0)
print(result)

result = db.query('alice', 'neighbors', node_id=0, direction='out')
print(result)

result = db.query('bob', 'path', source=0, target=3, max_depth=5)
print(result)

# Get statistics
stats = db.get_graph_statistics()
print(stats)
```

## Project Structure

```
.
├── src/
│   ├── __init__.py          # Package initialization
│   ├── data_loader.py       # Graph data loading
│   ├── preprocessing.py     # Data preprocessing with Dask
│   ├── indexing.py          # Graph indexing
│   ├── query_engine.py      # Query execution
│   ├── security.py          # Access control
│   ├── evaluation.py        # Performance metrics
│   └── graph_database.py    # Main database class
├── templates/
│   └── index.html           # Web interface template
├── app.py                   # Flask web application
├── main.py                  # CLI entry point
├── example.py               # Example usage script
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
└── README.md               # This file
```

## Performance Considerations

- **Memory**: The system uses efficient data structures (sets, dictionaries) for indexing
- **Scalability**: Dask enables processing of graphs larger than available RAM
- **Query Speed**: Adjacency list indexes provide O(1) neighbor lookups
- **Path Finding**: BFS-based path finding with configurable depth limits

## Web Interface Features

The Flask web interface provides:

- **📁 Graph Loading**: Upload and index graph files through the browser
- **🔍 Interactive Queries**: Execute all query types with a user-friendly form
- **📊 Real-time Statistics**: View graph statistics instantly
- **⚡ Performance Benchmarks**: Run benchmarks and view results
- **🎨 Modern UI**: Clean, responsive design with gradient styling

### Starting the Web Server

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## Docker Deployment

Build the Docker image:
```bash
docker build -t graph-db .
```

Run a container with web interface:
```bash
docker run -p 5000:5000 -v $(pwd)/data:/app/data graph-db python app.py
```

Or use CLI:
```bash
docker run -v $(pwd)/data:/app/data graph-db python main.py load /app/data/graph.csv
```

## Limitations

- Designed for read-heavy workloads
- Path queries use BFS (may be slow for very large graphs)
- No distributed processing (single machine)
- Basic security features (not production-ready)

## License

This is a prototype system for educational and research purposes.

## Contributing

This is a prototype system. For production use, consider:
- Adding persistent storage (database backend)
- Implementing more sophisticated query algorithms
- Adding distributed processing capabilities
- Enhancing security features

