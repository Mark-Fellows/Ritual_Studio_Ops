"""
Momence Service Client

A Python client library for querying the Momence Data Service.
Use this in your other programs to easily retrieve Momence data.

USAGE:
    from momence_service_client import MomenceServiceClient
    
    # Connect to the service
    client = MomenceServiceClient()  # defaults to localhost:5050
    # or
    client = MomenceServiceClient('http://192.168.1.100:5050')
    
    # Get members
    members = client.get_members(page=0, page_size=100)
    
    # Get a specific member
    member = client.get_member(12345)
    
    # Get sessions with date filter
    sessions = client.get_sessions(
        starts_after='2025-01-01',
        starts_before='2025-12-31'
    )
    
    # Export all data
    all_members = client.export_all_members()
    all_tags = client.export_all_tags()
"""

import requests
from typing import Optional, Dict, List, Any, Iterator
from datetime import datetime


class MomenceServiceError(Exception):
    """Base exception for service errors."""
    pass


class MomenceServiceClient:
    """
    Client for querying the Momence Data Service.
    
    This client communicates with the REST API service and provides
    a convenient Python interface for retrieving Momence data.
    """
    
    def __init__(self, base_url: str = "http://localhost:5050", timeout: int = 30):
        """
        Initialize the client.
        
        Args:
            base_url: URL of the Momence Data Service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session = requests.Session()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make a request to the service."""
        url = f"{self.base_url}/api{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    raise MomenceServiceError(
                        f"HTTP {e.response.status_code}: {error_data.get('error', str(e))}"
                    )
                except ValueError:
                    pass
            raise MomenceServiceError(str(e))
        except requests.exceptions.RequestException as e:
            raise MomenceServiceError(f"Connection error: {e}")
    
    # -------------------------------------------------------------------------
    # Health & Info
    # -------------------------------------------------------------------------
    
    def health(self) -> Dict:
        """Check service health."""
        return self._request('GET', '/health')
    
    def info(self) -> Dict:
        """Get service information and available endpoints."""
        return self._request('GET', '/info')
    
    def is_healthy(self) -> bool:
        """Quick health check returning boolean."""
        try:
            result = self.health()
            return result.get('status') == 'healthy'
        except MomenceServiceError:
            return False
    
    # -------------------------------------------------------------------------
    # Members
    # -------------------------------------------------------------------------
    
    def get_members(self, page: int = 0, page_size: int = 100) -> Dict:
        """
        Get paginated list of members.
        
        Args:
            page: Page number (0-indexed)
            page_size: Number of records per page (max 500)
        
        Returns:
            Dict with 'payload' (list of members) and 'pagination' info
        """
        params = {'page': page, 'page_size': min(page_size, 500)}
        return self._request('GET', '/members', params=params)
    
    def get_member(self, member_id: int) -> Dict:
        """
        Get a single member by ID.
        
        Args:
            member_id: The member's unique ID
        
        Returns:
            Member data including customerFields and customerTags
        """
        return self._request('GET', f'/members/{member_id}')
    
    def get_member_sessions(
        self,
        member_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> Dict:
        """
        Get booking history for a specific member.
        
        Args:
            member_id: The member's unique ID
            page: Page number
            page_size: Records per page
        
        Returns:
            Dict with member's session bookings
        """
        params = {'page': page, 'page_size': page_size}
        return self._request('GET', f'/members/{member_id}/sessions', params=params)
    
    def search_members(self, **filters) -> Dict:
        """
        Search members with filters.
        
        Args:
            **filters: Filter parameters (depends on API support)
        
        Returns:
            Filtered member list
        """
        return self._request('POST', '/members/search', json=filters)
    
    def iter_all_members(self, page_size: int = 500) -> Iterator[Dict]:
        """
        Iterate through all members (handles pagination automatically).
        
        Args:
            page_size: Records per page
        
        Yields:
            Individual member records
        """
        page = 0
        while True:
            result = self.get_members(page=page, page_size=page_size)
            members = result.get('payload', [])
            
            for member in members:
                yield member
            
            # Check if there are more pages
            pagination = result.get('pagination', {})
            total = pagination.get('totalCount', 0)
            if (page + 1) * page_size >= total:
                break
            
            page += 1
    
    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    
    def get_sessions(
        self,
        page: int = 0,
        page_size: int = 100,
        starts_after: str = None,
        starts_before: str = None
    ) -> Dict:
        """
        Get paginated list of sessions.
        
        Args:
            page: Page number (0-indexed)
            page_size: Number of records per page (max 500)
            starts_after: ISO date string filter (optional)
            starts_before: ISO date string filter (optional)
        
        Returns:
            Dict with 'payload' (list of sessions) and 'pagination' info
        """
        params = {'page': page, 'page_size': min(page_size, 500)}
        if starts_after:
            params['starts_after'] = starts_after
        if starts_before:
            params['starts_before'] = starts_before
        
        return self._request('GET', '/sessions', params=params)
    
    def get_session(self, session_id: int) -> Dict:
        """
        Get a single session by ID.
        
        Args:
            session_id: The session's unique ID
        
        Returns:
            Session data
        """
        return self._request('GET', f'/sessions/{session_id}')
    
    def get_session_bookings(
        self,
        session_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> Dict:
        """
        Get bookings for a specific session.
        
        Args:
            session_id: The session's unique ID
            page: Page number
            page_size: Records per page
        
        Returns:
            Dict with booking records including attendance status
        """
        params = {'page': page, 'page_size': page_size}
        return self._request('GET', f'/sessions/{session_id}/bookings', params=params)
    
    def iter_all_sessions(
        self,
        page_size: int = 500,
        starts_after: str = None,
        starts_before: str = None
    ) -> Iterator[Dict]:
        """
        Iterate through all sessions (handles pagination automatically).
        
        Args:
            page_size: Records per page
            starts_after: Optional start date filter
            starts_before: Optional end date filter
        
        Yields:
            Individual session records
        """
        page = 0
        while True:
            result = self.get_sessions(
                page=page,
                page_size=page_size,
                starts_after=starts_after,
                starts_before=starts_before
            )
            sessions = result.get('payload', [])
            
            for session in sessions:
                yield session
            
            pagination = result.get('pagination', {})
            total = pagination.get('totalCount', 0)
            if (page + 1) * page_size >= total:
                break
            
            page += 1
    
    # -------------------------------------------------------------------------
    # Memberships & Tags
    # -------------------------------------------------------------------------
    
    def get_memberships(self, page: int = 0, page_size: int = 100) -> Dict:
        """
        Get paginated list of membership product types.
        
        Args:
            page: Page number
            page_size: Records per page
        
        Returns:
            Dict with membership types (pricing, duration, etc.)
        """
        params = {'page': page, 'page_size': page_size}
        return self._request('GET', '/memberships', params=params)
    
    def get_tags(self, page: int = 0, page_size: int = 100) -> Dict:
        """
        Get paginated list of tags.
        
        Args:
            page: Page number
            page_size: Records per page
        
        Returns:
            Dict with tag definitions
        """
        params = {'page': page, 'page_size': page_size}
        return self._request('GET', '/tags', params=params)
    
    # -------------------------------------------------------------------------
    # Bulk Export
    # -------------------------------------------------------------------------
    
    def export_all_members(self) -> List[Dict]:
        """
        Export all members at once.
        
        Note: This may be slow for large datasets. Consider using
        iter_all_members() for streaming access.
        
        Returns:
            List of all member records
        """
        result = self._request('GET', '/export/members')
        return result.get('members', [])
    
    def export_all_memberships(self) -> List[Dict]:
        """Export all membership product types."""
        result = self._request('GET', '/export/memberships')
        return result.get('memberships', [])
    
    def export_all_tags(self) -> List[Dict]:
        """Export all tags."""
        result = self._request('GET', '/export/tags')
        return result.get('tags', [])
    
    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------
    
    def invalidate_cache(self, pattern: str = None) -> Dict:
        """
        Invalidate cache entries on the server.
        
        Args:
            pattern: Optional pattern to match (None = clear all)
        
        Returns:
            Confirmation dict
        """
        return self._request('POST', '/cache/invalidate', json={'pattern': pattern})
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics from the server."""
        return self._request('GET', '/cache/stats')


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def connect(url: str = "http://localhost:5050") -> MomenceServiceClient:
    """
    Create and return a connected client.
    
    Args:
        url: Service URL
    
    Returns:
        MomenceServiceClient instance
    
    Raises:
        MomenceServiceError: If service is not reachable
    """
    client = MomenceServiceClient(url)
    if not client.is_healthy():
        raise MomenceServiceError(f"Service at {url} is not responding")
    return client


def quick_export_members(url: str = "http://localhost:5050") -> List[Dict]:
    """Quick utility to export all members."""
    return MomenceServiceClient(url).export_all_members()


def quick_export_sessions(
    url: str = "http://localhost:5050",
    starts_after: str = None,
    starts_before: str = None
) -> List[Dict]:
    """Quick utility to export sessions."""
    client = MomenceServiceClient(url)
    return list(client.iter_all_sessions(
        starts_after=starts_after,
        starts_before=starts_before
    ))


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Example: Connect and retrieve data
    print("Momence Service Client - Example Usage")
    print("=" * 50)
    
    try:
        # Connect to service
        client = connect()
        print("✓ Connected to service")
        
        # Get health status
        health = client.health()
        print(f"✓ Service status: {health['status']}")
        
        # Get some members
        members = client.get_members(page=0, page_size=5)
        print(f"✓ Retrieved {len(members['payload'])} members")
        print(f"  Total available: {members['pagination']['totalCount']}")
        
        # Get memberships
        memberships = client.get_memberships(page=0, page_size=5)
        print(f"✓ Retrieved {len(memberships['payload'])} membership types")
        
        # Get tags
        tags = client.get_tags(page=0, page_size=5)
        print(f"✓ Retrieved {len(tags['payload'])} tags")
        
        print()
        print("Service is working correctly!")
        
    except MomenceServiceError as e:
        print(f"✗ Error: {e}")
        print()
        print("Make sure the service is running:")
        print("  python momence_data_service.py")
