"""
Momence Data Service

A robust REST API service that other programs can query to retrieve Momence data.
Provides caching, rate limiting, and multiple data formats.

USAGE:
    # Start the server
    python momence_data_service.py
    
    # Or run as module
    python -m momence_data_service
    
    # Query from another program (examples):
    GET http://localhost:5050/api/members
    GET http://localhost:5050/api/members?page=0&page_size=100
    GET http://localhost:5050/api/members/12345
    GET http://localhost:5050/api/sessions?starts_after=2025-01-01&starts_before=2025-12-31
    GET http://localhost:5050/api/sessions/12345/bookings
    GET http://localhost:5050/api/memberships
    GET http://localhost:5050/api/tags
    GET http://localhost:5050/api/health
    
DEPENDENCIES:
    pip install flask requests python-dotenv
"""

import os
import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, List, Callable
from threading import Lock
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv

# Import the existing API client
from momence_api_client import MomenceAPIClient, AuthenticationError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MomenceDataService')

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Service configuration."""
    HOST = os.getenv('MOMENCE_SERVICE_HOST', '0.0.0.0')
    PORT = int(os.getenv('MOMENCE_SERVICE_PORT', 5050))
    DEBUG = os.getenv('MOMENCE_SERVICE_DEBUG', 'false').lower() == 'true'
    
    # Cache settings
    CACHE_ENABLED = os.getenv('MOMENCE_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_DB_PATH = os.getenv('MOMENCE_CACHE_DB', 'momence_service_cache.db')
    CACHE_TTL_SECONDS = int(os.getenv('MOMENCE_CACHE_TTL', 300))  # 5 minutes default
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.getenv('MOMENCE_RATE_LIMIT', 'true').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.getenv('MOMENCE_RATE_LIMIT_REQUESTS', 60))
    RATE_LIMIT_WINDOW = int(os.getenv('MOMENCE_RATE_LIMIT_WINDOW', 60))  # seconds


# =============================================================================
# CACHE LAYER
# =============================================================================

class CacheManager:
    """SQLite-based cache for API responses."""
    
    def __init__(self, db_path: str, ttl_seconds: int = 300):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize the cache database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)')
            conn.commit()
    
    def _generate_key(self, endpoint: str, params: Dict) -> str:
        """Generate a cache key from endpoint and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        key_str = f"{endpoint}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Retrieve cached data if valid."""
        params = params or {}
        key = self._generate_key(endpoint, params)
        now = datetime.utcnow().isoformat()
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT value FROM cache WHERE key = ? AND expires_at > ?',
                    (key, now)
                )
                row = cursor.fetchone()
                if row:
                    logger.debug(f"Cache HIT: {endpoint}")
                    return json.loads(row[0])
        
        logger.debug(f"Cache MISS: {endpoint}")
        return None
    
    def set(self, endpoint: str, params: Dict, data: Dict, ttl: int = None):
        """Store data in cache."""
        params = params or {}
        key = self._generate_key(endpoint, params)
        ttl = ttl or self.ttl_seconds
        
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                ''', (key, json.dumps(data), now.isoformat(), expires_at.isoformat()))
                conn.commit()
        
        logger.debug(f"Cache SET: {endpoint} (TTL: {ttl}s)")
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries. If pattern is None, clear all."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                if pattern:
                    conn.execute('DELETE FROM cache WHERE key LIKE ?', (f'%{pattern}%',))
                else:
                    conn.execute('DELETE FROM cache')
                conn.commit()
        logger.info(f"Cache invalidated: {pattern or 'ALL'}")
    
    def cleanup_expired(self):
        """Remove expired cache entries."""
        now = datetime.utcnow().isoformat()
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM cache WHERE expires_at < ?', (now,))
                count = cursor.rowcount
                conn.commit()
        if count > 0:
            logger.info(f"Cache cleanup: removed {count} expired entries")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute('SELECT COUNT(*) FROM cache').fetchone()[0]
            valid = conn.execute('SELECT COUNT(*) FROM cache WHERE expires_at > ?', (now,)).fetchone()[0]
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': total - valid,
            'ttl_seconds': self.ttl_seconds
        }


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[datetime]] = {}
        self._lock = Lock()
    
    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        Returns (allowed, remaining_requests).
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        with self._lock:
            if client_id not in self._requests:
                self._requests[client_id] = []
            
            # Clean old requests
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]
            
            # Check limit
            if len(self._requests[client_id]) >= self.max_requests:
                return False, 0
            
            # Record this request
            self._requests[client_id].append(now)
            remaining = self.max_requests - len(self._requests[client_id])
            return True, remaining


# =============================================================================
# DATA SERVICE
# =============================================================================

class MomenceDataService:
    """
    Main data service that wraps the Momence API client with caching and 
    convenience methods.
    """
    
    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 300):
        self._client: Optional[MomenceAPIClient] = None
        self._authenticated = False
        self._lock = Lock()
        
        # Initialize cache
        self.cache_enabled = cache_enabled
        self.cache = CacheManager(Config.CACHE_DB_PATH, cache_ttl) if cache_enabled else None
    
    def _ensure_authenticated(self):
        """Ensure the API client is authenticated."""
        with self._lock:
            if self._client is None:
                self._client = MomenceAPIClient()
            
            if not self._authenticated or self._client._token_expires_at < datetime.now():
                self._client.authenticate()
                self._authenticated = True
    
    def _cached_request(self, endpoint: str, params: Dict, fetcher: Callable, ttl: int = None) -> Dict:
        """Execute a request with caching."""
        # Check cache first
        if self.cache_enabled and self.cache:
            cached = self.cache.get(endpoint, params)
            if cached:
                cached['_cached'] = True
                return cached
        
        # Fetch fresh data
        self._ensure_authenticated()
        data = fetcher()
        data['_cached'] = False
        
        # Store in cache
        if self.cache_enabled and self.cache:
            self.cache.set(endpoint, params, data, ttl)
        
        return data
    
    # -------------------------------------------------------------------------
    # MEMBERS
    # -------------------------------------------------------------------------
    
    def get_members(self, page: int = 0, page_size: int = 100) -> Dict:
        """Get paginated list of members."""
        params = {'page': page, 'page_size': page_size}
        return self._cached_request(
            'members',
            params,
            lambda: self._client.get_members(page, page_size)
        )
    
    def get_member(self, member_id: int) -> Dict:
        """Get a single member by ID."""
        params = {'member_id': member_id}
        
        def fetch():
            self._ensure_authenticated()
            url = f"{self._client.BASE_URL}/api/v2/host/members/{member_id}"
            headers = {'Authorization': f'Bearer {self._client._access_token}'}
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        
        return self._cached_request(f'member/{member_id}', params, fetch)
    
    def get_member_sessions(self, member_id: int, page: int = 0, page_size: int = 100) -> Dict:
        """Get booking history for a specific member."""
        params = {'member_id': member_id, 'page': page, 'page_size': page_size}
        return self._cached_request(
            f'member/{member_id}/sessions',
            params,
            lambda: self._client.get_member_sessions(member_id, page, page_size)
        )
    
    def search_members(self, filters: Dict) -> Dict:
        """Search members with filters using POST endpoint."""
        def fetch():
            self._ensure_authenticated()
            import requests as req
            url = f"{self._client.BASE_URL}/api/v2/host/members/list"
            headers = {'Authorization': f'Bearer {self._client._access_token}'}
            payload = {
                'page': filters.get('page', 0),
                'pageSize': filters.get('page_size', 100),
                **{k: v for k, v in filters.items() if k not in ['page', 'page_size']}
            }
            resp = req.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
        
        # Shorter cache for search results
        return self._cached_request('members/search', filters, fetch, ttl=60)
    
    # -------------------------------------------------------------------------
    # SESSIONS
    # -------------------------------------------------------------------------
    
    def get_sessions(
        self,
        page: int = 0,
        page_size: int = 100,
        starts_after: str = None,
        starts_before: str = None
    ) -> Dict:
        """Get paginated list of sessions with optional date filters."""
        params = {
            'page': page,
            'page_size': page_size,
            'starts_after': starts_after,
            'starts_before': starts_before
        }
        return self._cached_request(
            'sessions',
            params,
            lambda: self._client.get_sessions(page, page_size, starts_after, starts_before)
        )
    
    def get_session(self, session_id: int) -> Dict:
        """Get a single session by ID."""
        params = {'session_id': session_id}
        
        def fetch():
            self._ensure_authenticated()
            url = f"{self._client.BASE_URL}/api/v2/host/sessions/{session_id}"
            headers = {'Authorization': f'Bearer {self._client._access_token}'}
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
        
        return self._cached_request(f'session/{session_id}', params, fetch)
    
    def get_session_bookings(self, session_id: int, page: int = 0, page_size: int = 100) -> Dict:
        """Get bookings for a specific session."""
        params = {'session_id': session_id, 'page': page, 'page_size': page_size}
        return self._cached_request(
            f'session/{session_id}/bookings',
            params,
            lambda: self._client.get_session_bookings(session_id, page, page_size)
        )
    
    # -------------------------------------------------------------------------
    # MEMBERSHIPS & TAGS
    # -------------------------------------------------------------------------
    
    def get_memberships(self, page: int = 0, page_size: int = 100) -> Dict:
        """Get paginated list of membership product types."""
        params = {'page': page, 'page_size': page_size}
        # Longer TTL for memberships (they change rarely)
        return self._cached_request(
            'memberships',
            params,
            lambda: self._client.get_memberships(page, page_size),
            ttl=3600  # 1 hour
        )
    
    def get_tags(self, page: int = 0, page_size: int = 100) -> Dict:
        """Get paginated list of tags."""
        params = {'page': page, 'page_size': page_size}
        # Longer TTL for tags
        return self._cached_request(
            'tags',
            params,
            lambda: self._client.get_tags(page, page_size),
            ttl=3600  # 1 hour
        )
    
    # -------------------------------------------------------------------------
    # BULK DATA RETRIEVAL
    # -------------------------------------------------------------------------
    
    def get_all_members(self, progress_callback: Callable = None) -> List[Dict]:
        """Retrieve all members (auto-paginated)."""
        self._ensure_authenticated()
        return self._client.get_all_members()
    
    def get_all_memberships(self) -> List[Dict]:
        """Retrieve all membership types."""
        self._ensure_authenticated()
        return self._client.get_all_memberships()
    
    def get_all_tags(self) -> List[Dict]:
        """Retrieve all tags."""
        self._ensure_authenticated()
        return self._client.get_all_tags()
    
    # -------------------------------------------------------------------------
    # CACHE MANAGEMENT
    # -------------------------------------------------------------------------
    
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cache entries."""
        if self.cache:
            self.cache.invalidate(pattern)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {'enabled': False}


# =============================================================================
# FLASK REST API
# =============================================================================

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Initialize service
    service = MomenceDataService(
        cache_enabled=Config.CACHE_ENABLED,
        cache_ttl=Config.CACHE_TTL_SECONDS
    )
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(
        Config.RATE_LIMIT_REQUESTS,
        Config.RATE_LIMIT_WINDOW
    ) if Config.RATE_LIMIT_ENABLED else None
    
    # -------------------------------------------------------------------------
    # Middleware
    # -------------------------------------------------------------------------
    
    @app.before_request
    def check_rate_limit():
        """Check rate limit before processing request."""
        if rate_limiter:
            client_id = request.remote_addr
            allowed, remaining = rate_limiter.is_allowed(client_id)
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': Config.RATE_LIMIT_WINDOW
                }), 429
    
    @app.after_request
    def add_headers(response):
        """Add standard headers to all responses."""
        response.headers['X-Service'] = 'Momence-Data-Service'
        response.headers['X-Cache-Enabled'] = str(Config.CACHE_ENABLED)
        return response
    
    # -------------------------------------------------------------------------
    # Error Handlers
    # -------------------------------------------------------------------------
    
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(e):
        return jsonify({'error': 'Authentication failed', 'message': str(e)}), 401
    
    @app.errorhandler(Exception)
    def handle_error(e):
        logger.exception(f"Unhandled error: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500
    
    # -------------------------------------------------------------------------
    # Health & Info Endpoints
    # -------------------------------------------------------------------------
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'cache': service.get_cache_stats()
        })
    
    @app.route('/api/info', methods=['GET'])
    def service_info():
        """Service information and available endpoints."""
        return jsonify({
            'service': 'Momence Data Service',
            'version': '1.0.0',
            'endpoints': {
                'GET /api/health': 'Health check',
                'GET /api/info': 'Service information',
                'GET /api/members': 'List members (paginated)',
                'GET /api/members/<id>': 'Get single member',
                'GET /api/members/<id>/sessions': 'Get member booking history',
                'POST /api/members/search': 'Search members with filters',
                'GET /api/sessions': 'List sessions (paginated)',
                'GET /api/sessions/<id>': 'Get single session',
                'GET /api/sessions/<id>/bookings': 'Get session bookings',
                'GET /api/memberships': 'List membership products',
                'GET /api/tags': 'List tags',
                'POST /api/cache/invalidate': 'Invalidate cache',
                'GET /api/export/members': 'Export all members (JSON)',
                'GET /api/export/memberships': 'Export all memberships',
                'GET /api/export/tags': 'Export all tags',
            }
        })
    
    # -------------------------------------------------------------------------
    # Members Endpoints
    # -------------------------------------------------------------------------
    
    @app.route('/api/members', methods=['GET'])
    def list_members():
        """Get paginated list of members."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        page_size = min(page_size, 500)  # Cap at 500
        
        data = service.get_members(page, page_size)
        return jsonify(data)
    
    @app.route('/api/members/<int:member_id>', methods=['GET'])
    def get_member(member_id: int):
        """Get a single member by ID."""
        data = service.get_member(member_id)
        return jsonify(data)
    
    @app.route('/api/members/<int:member_id>/sessions', methods=['GET'])
    def get_member_sessions(member_id: int):
        """Get booking history for a member."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        
        data = service.get_member_sessions(member_id, page, page_size)
        return jsonify(data)
    
    @app.route('/api/members/search', methods=['POST'])
    def search_members():
        """Search members with filters."""
        filters = request.get_json() or {}
        data = service.search_members(filters)
        return jsonify(data)
    
    # -------------------------------------------------------------------------
    # Sessions Endpoints
    # -------------------------------------------------------------------------
    
    @app.route('/api/sessions', methods=['GET'])
    def list_sessions():
        """Get paginated list of sessions."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        page_size = min(page_size, 500)
        starts_after = request.args.get('starts_after')
        starts_before = request.args.get('starts_before')
        
        data = service.get_sessions(page, page_size, starts_after, starts_before)
        return jsonify(data)
    
    @app.route('/api/sessions/<int:session_id>', methods=['GET'])
    def get_session(session_id: int):
        """Get a single session by ID."""
        data = service.get_session(session_id)
        return jsonify(data)
    
    @app.route('/api/sessions/<int:session_id>/bookings', methods=['GET'])
    def get_session_bookings(session_id: int):
        """Get bookings for a session."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        
        data = service.get_session_bookings(session_id, page, page_size)
        return jsonify(data)
    
    # -------------------------------------------------------------------------
    # Memberships & Tags Endpoints
    # -------------------------------------------------------------------------
    
    @app.route('/api/memberships', methods=['GET'])
    def list_memberships():
        """Get paginated list of membership products."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        
        data = service.get_memberships(page, page_size)
        return jsonify(data)
    
    @app.route('/api/tags', methods=['GET'])
    def list_tags():
        """Get paginated list of tags."""
        page = request.args.get('page', 0, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        
        data = service.get_tags(page, page_size)
        return jsonify(data)
    
    # -------------------------------------------------------------------------
    # Export Endpoints (Bulk Data)
    # -------------------------------------------------------------------------
    
    @app.route('/api/export/members', methods=['GET'])
    def export_all_members():
        """Export all members as JSON (streaming)."""
        def generate():
            yield '{"members": ['
            first = True
            for member in service.get_all_members():
                if not first:
                    yield ','
                yield json.dumps(member)
                first = False
            yield ']}'
        
        return Response(generate(), mimetype='application/json')
    
    @app.route('/api/export/memberships', methods=['GET'])
    def export_all_memberships():
        """Export all membership products."""
        data = service.get_all_memberships()
        return jsonify({'memberships': data, 'count': len(data)})
    
    @app.route('/api/export/tags', methods=['GET'])
    def export_all_tags():
        """Export all tags."""
        data = service.get_all_tags()
        return jsonify({'tags': data, 'count': len(data)})
    
    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------
    
    @app.route('/api/cache/invalidate', methods=['POST'])
    def invalidate_cache():
        """Invalidate cache entries."""
        data = request.get_json() or {}
        pattern = data.get('pattern')
        service.invalidate_cache(pattern)
        return jsonify({'success': True, 'pattern': pattern or 'ALL'})
    
    @app.route('/api/cache/stats', methods=['GET'])
    def cache_stats():
        """Get cache statistics."""
        return jsonify(service.get_cache_stats())
    
    return app


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Momence Data Service')
    parser.add_argument('--host', default=Config.HOST, help='Host to bind to')
    parser.add_argument('--port', type=int, default=Config.PORT, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    
    args = parser.parse_args()
    
    # Update config
    if args.no_cache:
        Config.CACHE_ENABLED = False
    
    # Create and run app
    app = create_app()
    
    print("=" * 60)
    print("MOMENCE DATA SERVICE")
    print("=" * 60)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Cache: {'Enabled' if Config.CACHE_ENABLED else 'Disabled'}")
    print(f"Rate Limiting: {'Enabled' if Config.RATE_LIMIT_ENABLED else 'Disabled'}")
    print()
    print("Endpoints:")
    print("  GET  /api/health              - Health check")
    print("  GET  /api/info                - Service info")
    print("  GET  /api/members             - List members")
    print("  GET  /api/members/<id>        - Get member")
    print("  GET  /api/sessions            - List sessions")
    print("  GET  /api/sessions/<id>       - Get session")
    print("  GET  /api/memberships         - List membership products")
    print("  GET  /api/tags                - List tags")
    print("  GET  /api/export/members      - Export all members")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
