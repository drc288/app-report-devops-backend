"""
GitHub App Authentication Module

This module handles GitHub App authentication, including:
- JWT token generation for GitHub App
- Installation access token management
- Rate limit handling for GitHub Apps
- Automatic token refresh
"""

import jwt
import time
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from pathlib import Path
from fastapi import HTTPException
from ..schemas.settings import Settings


class GitHubAppAuth:
    """
    GitHub App Authentication handler

    Manages JWT tokens and installation access tokens for GitHub App API access
    """

    def __init__(self, app_id: str, private_key_path: str, installation_id: Optional[str] = None):
        self.app_id = app_id
        self.private_key_path = private_key_path
        self.installation_id = installation_id
        self._private_key = None
        self._installation_token = None
        self._installation_token_expires = None
        self._jwt_token = None
        self._jwt_expires = None

    def _load_private_key(self) -> str:
        """Load the private key from file"""
        if self._private_key is None:
            try:
                key_path = Path(self.private_key_path)
                if not key_path.exists():
                    raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")

                with open(key_path, 'r') as key_file:
                    self._private_key = key_file.read()
            except Exception as e:
                raise HTTPException(500, f"Error loading private key: {str(e)}")

        return self._private_key

    def _generate_jwt_token(self) -> str:
        """Generate a JWT token for GitHub App authentication"""
        now = int(time.time())

        # JWT expires in 10 minutes (GitHub's maximum)
        expiration = now + (10 * 60)

        payload = {
            'iat': now - 60,  # Issued at time (1 minute ago to account for clock drift)
            'exp': expiration,  # Expiration time
            'iss': self.app_id  # Issuer (App ID)
        }

        private_key = self._load_private_key()

        try:
            token = jwt.encode(payload, private_key, algorithm='RS256')
            self._jwt_token = token
            self._jwt_expires = datetime.fromtimestamp(expiration, tz=timezone.utc)
            return token
        except Exception as e:
            raise HTTPException(500, f"Error generating JWT token: {str(e)}")

    def get_jwt_token(self) -> str:
        """Get a valid JWT token, generating a new one if necessary"""
        if (self._jwt_token is None or
            self._jwt_expires is None or
            datetime.now(timezone.utc) >= self._jwt_expires - timedelta(minutes=2)):
            # Generate new token if it doesn't exist or expires in less than 2 minutes
            return self._generate_jwt_token()

        return self._jwt_token

    async def _get_installation_id(self) -> str:
        """Get the installation ID for the organization"""
        if self.installation_id:
            return self.installation_id

        # If no installation ID provided, try to get it from the organization
        settings = Settings()
        jwt_token = self.get_jwt_token()

        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get installations for this app
                response = await client.get(
                    'https://api.github.com/app/installations',
                    headers=headers
                )
                response.raise_for_status()

                installations = response.json()

                # Find installation for our organization
                for installation in installations:
                    if installation.get('account', {}).get('login') == settings.github_org:
                        self.installation_id = str(installation['id'])
                        return self.installation_id

                raise HTTPException(
                    404,
                    f"No GitHub App installation found for organization: {settings.github_org}"
                )

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                e.response.status_code,
                f"Error getting installation ID: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(500, f"Unexpected error getting installation ID: {str(e)}")

    async def _get_installation_access_token(self) -> str:
        """Get an installation access token"""
        try:
            installation_id = await self._get_installation_id()
            jwt_token = self.get_jwt_token()
            
            headers = {
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f'https://api.github.com/app/installations/{installation_id}/access_tokens',
                    headers=headers
                )
                response.raise_for_status()
                
                token_data = response.json()
                
                if 'token' not in token_data:
                    raise HTTPException(500, "No token in response from GitHub")
                
                self._installation_token = token_data['token']
                # GitHub installation tokens expire in 1 hour
                expires_at = token_data['expires_at']
                if expires_at.endswith('Z'):
                    expires_at = expires_at[:-1] + '+00:00'
                self._installation_token_expires = datetime.fromisoformat(expires_at)
                
                return self._installation_token
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise HTTPException(e.response.status_code, f"Error getting installation access token: {error_msg}")
        except Exception as e:
            raise HTTPException(500, f"Unexpected error getting installation access token: {str(e)}")

    async def get_installation_token(self) -> str:
        """Get a valid installation access token, refreshing if necessary"""
        if (self._installation_token is None or
            self._installation_token_expires is None or
            datetime.now(timezone.utc) >= self._installation_token_expires - timedelta(minutes=5)):
            # Get new token if it doesn't exist or expires in less than 5 minutes
            return await self._get_installation_access_token()

        return self._installation_token

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for GitHub API requests"""
        token = await self.get_installation_token()

        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'GitHubApp-DevOps-Reporter'
        }

    async def get_rate_limit_info(self) -> Dict:
        """Get current rate limit information for the GitHub App"""
        headers = await self.get_auth_headers()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    'https://api.github.com/rate_limit',
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                e.response.status_code,
                f"Error getting rate limit info: {e.response.text}"
            )

    def get_auth_info(self) -> Dict:
        """Get information about current authentication state"""
        now = datetime.now(timezone.utc)
        return {
            'app_id': self.app_id,
            'installation_id': self.installation_id,
            'jwt_token_expires': self._jwt_expires.isoformat() if self._jwt_expires else None,
            'installation_token_expires': self._installation_token_expires.isoformat() if self._installation_token_expires else None,
            'has_jwt_token': self._jwt_token is not None,
            'has_installation_token': self._installation_token is not None,
            'current_time': now.isoformat(),
            'jwt_valid': self._jwt_expires and now < self._jwt_expires if self._jwt_expires else False,
            'installation_token_valid': self._installation_token_expires and now < self._installation_token_expires if self._installation_token_expires else False
        }