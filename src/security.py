"""
Security and Access Control Module
Implements basic access control and query restrictions.
"""

from typing import Set, Optional, Dict, Callable, Tuple
from enum import Enum
import time
from functools import wraps


class Permission(Enum):
    """Permission levels for users."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class AccessControl:
    """
    Basic access control system for graph queries.
    Manages user permissions and query restrictions.
    """
    
    def __init__(self):
        """Initialize access control system."""
        self.users: Dict[str, Permission] = {}
        self.query_limits: Dict[str, int] = {}  # user -> query count
        self.query_history: Dict[str, list] = {}  # user -> list of queries
        self.blocked_nodes: Set[int] = set()  # Nodes that cannot be queried
        self.blocked_edges: Set[tuple] = set()  # Edges that cannot be queried
        self.rate_limits: Dict[str, Dict] = {}  # user -> {limit: int, window: int}
    
    def add_user(self, user_id: str, permission: Permission = Permission.READ_ONLY):
        """
        Add a user with specified permission level.
        
        Args:
            user_id: Unique user identifier
            permission: Permission level for the user
        """
        self.users[user_id] = permission
        self.query_limits[user_id] = 0
        self.query_history[user_id] = []
        print(f"Added user {user_id} with permission {permission.value}")
    
    def remove_user(self, user_id: str):
        """
        Remove a user from the system.
        
        Args:
            user_id: User identifier to remove
        """
        if user_id in self.users:
            del self.users[user_id]
            del self.query_limits[user_id]
            del self.query_history[user_id]
            if user_id in self.rate_limits:
                del self.rate_limits[user_id]
            print(f"Removed user {user_id}")
    
    def check_permission(self, user_id: str, required_permission: Permission) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_id: User identifier
            required_permission: Required permission level
        
        Returns:
            True if user has permission, False otherwise
        """
        if user_id not in self.users:
            return False
        
        user_permission = self.users[user_id]
        
        # Permission hierarchy: READ_ONLY < READ_WRITE < ADMIN
        permission_levels = {
            Permission.READ_ONLY: 1,
            Permission.READ_WRITE: 2,
            Permission.ADMIN: 3
        }
        
        return permission_levels[user_permission] >= permission_levels[required_permission]
    
    def block_node(self, node_id: int):
        """
        Block access to a specific node.
        
        Args:
            node_id: Node ID to block
        """
        self.blocked_nodes.add(node_id)
        print(f"Blocked access to node {node_id}")
    
    def unblock_node(self, node_id: int):
        """
        Unblock access to a specific node.
        
        Args:
            node_id: Node ID to unblock
        """
        self.blocked_nodes.discard(node_id)
        print(f"Unblocked access to node {node_id}")
    
    def block_edge(self, source: int, target: int):
        """
        Block access to a specific edge.
        
        Args:
            source: Source node ID
            target: Target node ID
        """
        self.blocked_edges.add((source, target))
        print(f"Blocked access to edge ({source}, {target})")
    
    def is_node_blocked(self, node_id: int) -> bool:
        """
        Check if a node is blocked.
        
        Args:
            node_id: Node ID to check
        
        Returns:
            True if blocked, False otherwise
        """
        return node_id in self.blocked_nodes
    
    def is_edge_blocked(self, source: int, target: int) -> bool:
        """
        Check if an edge is blocked.
        
        Args:
            source: Source node ID
            target: Target node ID
        
        Returns:
            True if blocked, False otherwise
        """
        return (source, target) in self.blocked_edges
    
    def set_rate_limit(self, user_id: str, max_queries: int, window_seconds: int = 60):
        """
        Set rate limit for a user.
        
        Args:
            user_id: User identifier
            max_queries: Maximum number of queries allowed
            window_seconds: Time window in seconds
        """
        self.rate_limits[user_id] = {
            'max_queries': max_queries,
            'window_seconds': window_seconds
        }
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
        
        Returns:
            Tuple of (allowed: bool, message: Optional[str])
        """
        if user_id not in self.rate_limits:
            return True, None
        
        limit_config = self.rate_limits[user_id]
        current_time = time.time()
        
        # Filter queries within the time window
        recent_queries = [
            q_time for q_time in self.query_history.get(user_id, [])
            if current_time - q_time < limit_config['window_seconds']
        ]
        
        if len(recent_queries) >= limit_config['max_queries']:
            return False, f"Rate limit exceeded: {limit_config['max_queries']} queries per {limit_config['window_seconds']} seconds"
        
        return True, None
    
    def record_query(self, user_id: str):
        """
        Record a query for rate limiting purposes.
        
        Args:
            user_id: User identifier
        """
        if user_id not in self.query_history:
            self.query_history[user_id] = []
        
        self.query_history[user_id].append(time.time())
        self.query_limits[user_id] += 1
    
    def get_user_stats(self, user_id: str) -> dict:
        """
        Get statistics for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary with user statistics
        """
        if user_id not in self.users:
            return {'error': 'User not found'}
        
        return {
            'user_id': user_id,
            'permission': self.users[user_id].value,
            'total_queries': self.query_limits.get(user_id, 0),
            'recent_queries': len(self.query_history.get(user_id, []))
        }


def require_permission(required_permission: Permission):
    """
    Decorator to require specific permission for a function.
    
    Args:
        required_permission: Required permission level
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, user_id: str, *args, **kwargs):
            if not hasattr(self, 'access_control'):
                raise AttributeError("Object must have 'access_control' attribute")
            
            if not self.access_control.check_permission(user_id, required_permission):
                return {
                    'error': 'Permission denied',
                    'required': required_permission.value,
                    'message': f'User {user_id} does not have {required_permission.value} permission'
                }
            
            # Check rate limit
            allowed, message = self.access_control.check_rate_limit(user_id)
            if not allowed:
                return {'error': 'Rate limit exceeded', 'message': message}
            
            # Record query
            self.access_control.record_query(user_id)
            
            return func(self, user_id, *args, **kwargs)
        
        return wrapper
    return decorator

