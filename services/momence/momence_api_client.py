"""
momence_api_client.py

A Python client for Momence API v2 using the Password Flow authentication.
This replaces the complex Selenium-based scraping with direct API calls.

SETUP:
1. Create a .env file with your credentials (see .env.example)
2. pip install requests python-dotenv
3. Run this script to test authentication

IMPORTANT: This uses the Password Flow which requires your Momence staff
account credentials (email/password), not just the OAuth client credentials.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the script's directory
script_dir = Path(__file__).parent
env_path = script_dir / '.env'
load_dotenv(dotenv_path=env_path)

class MomenceAPIClient:
    """Client for Momence API v2 with OAuth Password Flow authentication."""
    
    BASE_URL = "https://api.momence.com"
    TOKEN_ENDPOINT = "/api/v2/auth/token"
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        username: str = None,
        password: str = None,
        host_id: str = None
    ):
        """
        Initialize the Momence API client.
        
        Credentials can be passed directly or loaded from environment variables:
        - MOMENCE_CLIENT_ID
        - MOMENCE_CLIENT_SECRET
        - MOMENCE_USERNAME (your staff email)
        - MOMENCE_PASSWORD (your staff password)
        - MOMENCE_HOST_ID
        """
        self.client_id = client_id or os.getenv("MOMENCE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("MOMENCE_CLIENT_SECRET")
        self.username = username or os.getenv("MOMENCE_USERNAME")
        self.password = password or os.getenv("MOMENCE_PASSWORD")
        self.host_id = host_id or os.getenv("MOMENCE_HOST_ID")
        
        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Validate required credentials
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Ensure all required credentials are present."""
        missing = []
        if not self.client_id:
            missing.append("MOMENCE_CLIENT_ID")
        if not self.client_secret:
            missing.append("MOMENCE_CLIENT_SECRET")
        if not self.username:
            missing.append("MOMENCE_USERNAME")
        if not self.password:
            missing.append("MOMENCE_PASSWORD")
        if not self.host_id:
            missing.append("MOMENCE_HOST_ID")
        
        if missing:
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")
    
    def authenticate(self) -> bool:
        """
        Authenticate using the Password Flow.
        
        Returns True if successful, raises an exception otherwise.
        """
        print(f"[AUTH] Authenticating as {self.username}...")
        
        url = f"{self.BASE_URL}{self.TOKEN_ENDPOINT}"
        
        # Password flow requires these parameters
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        try:
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")
                
                # Calculate token expiry (usually a few hours)
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                print(f"[AUTH] SUCCESS: Authentication successful!")
                print(f"[AUTH]   Token expires in {expires_in} seconds")
                return True
            
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
                error_desc = error_data.get("error_description", "")
                
                print(f"[AUTH] FAILED: Authentication failed: {error_msg}")
                if error_desc:
                    print(f"[AUTH]   {error_desc}")
                
                # Common issues
                if "grant_type" in error_msg:
                    print("[AUTH]   Note: Momence only supports password, refresh_token, authorization_code")
                
                raise AuthenticationError(f"Authentication failed: {error_msg}")
            
            elif response.status_code == 401:
                print("[AUTH] FAILED: Invalid credentials")
                print("[AUTH]   Check your username (email) and password")
                raise AuthenticationError("Invalid username or password")
            
            else:
                print(f"[AUTH] FAILED: Unexpected response: {response.status_code}")
                print(f"[AUTH]   {response.text}")
                raise AuthenticationError(f"Unexpected response: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[AUTH] ✗ Network error: {e}")
            raise
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            print("[AUTH] No refresh token available, re-authenticating...")
            return self.authenticate()
        
        print("[AUTH] Refreshing access token...")
        
        url = f"{self.BASE_URL}{self.TOKEN_ENDPOINT}"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        try:
            response = requests.post(url, data=data, headers=headers)
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")
                
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
                
                print("[AUTH] SUCCESS: Token refreshed successfully")
                return True
            else:
                print(f"[AUTH] Refresh failed ({response.status_code}), re-authenticating...")
                return self.authenticate()
                
        except requests.exceptions.RequestException as e:
            print(f"[AUTH] Refresh error: {e}, re-authenticating...")
            return self.authenticate()
    
    def _ensure_valid_token(self):
        """Ensure we have a valid access token, refreshing if needed."""
        if not self._access_token:
            self.authenticate()
        elif self._token_expires_at and datetime.now() >= self._token_expires_at:
            self.refresh_access_token()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make an authenticated API request."""
        self._ensure_valid_token()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data
        )
        
        if response.status_code == 401:
            # Token might have expired, try refresh
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            )
        
        # Debug: print error details for non-2xx responses
        if not response.ok:
            print(f"  [DEBUG] Status: {response.status_code}")
            print(f"  [DEBUG] Response: {response.text[:500]}")
        
        response.raise_for_status()
        return response.json()
    
    # ========== Host API Methods ==========
    # Note: Host ID is NOT included in endpoint paths - it's derived from the authenticated staff user
    # Pagination uses 'page' (0-indexed) and 'pageSize' parameters
    
    def get_members(self, page: int = 0, page_size: int = 100) -> List[Dict]:
        """Get list of members (customers)."""
        endpoint = "/api/v2/host/members"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_sessions(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 0,
        page_size: int = 100
    ) -> List[Dict]:
        """Get list of sessions (classes)."""
        endpoint = "/api/v2/host/sessions"
        
        params = {"page": page, "pageSize": page_size}
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")
        
        return self._make_request("GET", endpoint, params=params)
    
    def get_session_bookings(
        self,
        session_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> List[Dict]:
        """Get session bookings for a specific session."""
        endpoint = f"/api/v2/host/sessions/{session_id}/bookings"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_memberships(
        self,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get available membership types/products.
        
        Returns membership definitions (not member purchases).
        Includes pricing, duration, credits, and contract details.
        """
        endpoint = "/api/v2/host/memberships"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_tags(
        self,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get available tags.
        
        Tags can be used for customers, sessions, and memberships.
        """
        endpoint = "/api/v2/host/tags"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_member_sessions(
        self,
        member_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get session bookings for a specific member.
        
        Returns booking history with nested session details.
        Alternative to get_session_bookings() - this queries by member instead of session.
        
        Args:
            member_id: The member ID from get_members()
            page: Page number (0-indexed)
            page_size: Results per page (max 100)
        """
        endpoint = f"/api/v2/host/members/{member_id}/sessions"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_member_notes(
        self,
        member_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get notes for a specific member.
        
        Args:
            member_id: The member ID from get_members()
        """
        endpoint = f"/api/v2/host/members/{member_id}/notes"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    def get_member_appointments(
        self,
        member_id: int,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get appointments for a specific member.
        
        Args:
            member_id: The member ID from get_members()
        """
        endpoint = f"/api/v2/host/members/{member_id}/appointments"
        params = {"page": page, "pageSize": page_size}
        return self._make_request("GET", endpoint, params=params)
    
    # ========== Convenience Methods ==========
    
    def get_all_members(self, page_size: int = 100) -> List[Dict]:
        """
        Fetch all members with automatic pagination.
        
        Warning: This may take a while for large datasets.
        """
        all_members = []
        page = 0
        while True:
            result = self.get_members(page=page, page_size=page_size)
            payload = result.get('payload', [])
            all_members.extend(payload)
            
            pagination = result.get('pagination', {})
            total = pagination.get('totalCount', 0)
            
            if len(all_members) >= total or len(payload) < page_size:
                break
            page += 1
            
        return all_members
    
    def get_all_memberships(self, page_size: int = 100) -> List[Dict]:
        """Fetch all membership types with automatic pagination."""
        all_memberships = []
        page = 0
        while True:
            result = self.get_memberships(page=page, page_size=page_size)
            payload = result.get('payload', [])
            all_memberships.extend(payload)
            
            pagination = result.get('pagination', {})
            total = pagination.get('totalCount', 0)
            
            if len(all_memberships) >= total or len(payload) < page_size:
                break
            page += 1
            
        return all_memberships
    
    def get_all_tags(self, page_size: int = 100) -> List[Dict]:
        """Fetch all tags with automatic pagination."""
        all_tags = []
        page = 0
        while True:
            result = self.get_tags(page=page, page_size=page_size)
            payload = result.get('payload', [])
            all_tags.extend(payload)
            
            pagination = result.get('pagination', {})
            total = pagination.get('totalCount', 0)
            
            if len(all_tags) >= total or len(payload) < page_size:
                break
            page += 1
            
        return all_tags


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


# ========== Test Script ==========

def main():
    """Test the Momence API client."""
    print("=" * 60)
    print("Momence API v2 - Full Endpoint Test")
    print("=" * 60)
    
    try:
        # Initialize client (loads from .env)
        client = MomenceAPIClient()
        
        # Authenticate
        client.authenticate()
        
        print("\n" + "=" * 60)
        print("Testing API Endpoints")
        print("=" * 60)
        
        # Test 1: Get members
        print("\n[TEST 1] Fetching members...")
        try:
            members = client.get_members(page=0, page_size=5)
            payload = members.get('payload', [])
            pagination = members.get('pagination', {})
            print(f"  OK: {len(payload)} members (total: {pagination.get('totalCount', '?')})")
            if payload:
                m = payload[0]
                print(f"  Sample: {m.get('firstName', 'N/A')} {m.get('lastName', '')} ({m.get('email', 'N/A')})")
                member_id = m['id']  # Save for later tests
        except Exception as e:
            print(f"  FAILED: {e}")
            member_id = None
        
        # Test 2: Get sessions
        print("\n[TEST 2] Fetching sessions...")
        try:
            now = datetime.now(timezone.utc)
            sessions = client.get_sessions(
                start_date=now,
                end_date=now + timedelta(days=7),
                page=0, page_size=5
            )
            payload = sessions.get('payload', [])
            pagination = sessions.get('pagination', {})
            print(f"  OK: {len(payload)} sessions (total: {pagination.get('totalCount', '?')})")
            if payload:
                s = payload[0]
                print(f"  Sample: {s.get('name', 'N/A')} at {s.get('startsAt', 'N/A')}")
        except Exception as e:
            print(f"  FAILED: {e}")
        
        # Test 3: Get memberships
        print("\n[TEST 3] Fetching memberships...")
        try:
            memberships = client.get_memberships(page=0, page_size=5)
            payload = memberships.get('payload', [])
            pagination = memberships.get('pagination', {})
            print(f"  OK: {len(payload)} memberships (total: {pagination.get('totalCount', '?')})")
            if payload:
                m = payload[0]
                print(f"  Sample: {m.get('name', 'N/A')} - ${m.get('price', 0)} ({m.get('type', 'N/A')})")
        except Exception as e:
            print(f"  FAILED: {e}")
        
        # Test 4: Get tags
        print("\n[TEST 4] Fetching tags...")
        try:
            tags = client.get_tags(page=0, page_size=5)
            payload = tags.get('payload', [])
            pagination = tags.get('pagination', {})
            print(f"  OK: {len(payload)} tags (total: {pagination.get('totalCount', '?')})")
            if payload:
                tag_names = [t.get('name', 'N/A') for t in payload[:3]]
                print(f"  Sample: {', '.join(tag_names)}")
        except Exception as e:
            print(f"  FAILED: {e}")
        
        # Test 5: Get member sessions (bookings by member)
        if member_id:
            print(f"\n[TEST 5] Fetching sessions for member {member_id}...")
            try:
                member_sessions = client.get_member_sessions(member_id=member_id, page=0, page_size=3)
                payload = member_sessions.get('payload', [])
                pagination = member_sessions.get('pagination', {})
                print(f"  OK: {len(payload)} bookings (total: {pagination.get('totalCount', '?')})")
                if payload:
                    b = payload[0]
                    sess = b.get('session', {})
                    print(f"  Sample: {sess.get('name', 'N/A')} - checkedIn={b.get('checkedIn', 'N/A')}")
            except Exception as e:
                print(f"  FAILED: {e}")
        
        print("\n" + "=" * 60)
        print("All tests complete!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n[ERROR] Configuration error: {e}")
        print("\nPlease create a .env file with your credentials:")
        print("  MOMENCE_CLIENT_ID=your-client-id")
        print("  MOMENCE_CLIENT_SECRET=your-client-secret")
        print("  MOMENCE_USERNAME=your-staff-email@example.com")
        print("  MOMENCE_PASSWORD=your-momence-password")
        print("  MOMENCE_HOST_ID=32083")
        
    except AuthenticationError as e:
        print(f"\n[ERROR] Authentication failed: {e}")
        print("\nPossible causes:")
        print("  1. Incorrect username (email) or password")
        print("  2. Account has 2FA enabled (may need different approach)")
        print("  3. Invalid OAuth client credentials")
        
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
