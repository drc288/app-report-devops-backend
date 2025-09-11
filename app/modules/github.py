from ..schemas.settings import Settings
from .github_app import GitHubAppAuth
import httpx
from fastapi import HTTPException
import base64
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class CacheEntry:
    def __init__(self, data, expiry_minutes: int = 30):
        self.data = data
        self.expiry = datetime.now() + timedelta(minutes=expiry_minutes)

    def is_expired(self) -> bool:
        return datetime.now() > self.expiry


class GithubClient:
    settings: Settings
    api_url = "https://api.github.com"

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._file_cache: Dict[str, CacheEntry] = {}
        self._github_app_auth = None

    async def _get_github_app_auth(self) -> GitHubAppAuth:
        """Get or create GitHub App authentication instance"""
        if self._github_app_auth is None:
            self._github_app_auth = GitHubAppAuth(
                app_id=self.settings.github_app_id,
                private_key_path=self.settings.github_app_private_key_path,
                installation_id=self.settings.github_app_installation_id or None
            )
        return self._github_app_auth

    async def header(self):
        """Get authentication headers - GitHub App or token based"""
        if self.settings.use_github_app:
            github_app = await self._get_github_app_auth()
            return await github_app.get_auth_headers()
        else:
            # Fallback to token authentication
            return {
                "Accept": "application/vnd.github+json",
                "User-Agent": "fastapi-client",
                "Authorization": f"Bearer {self.settings.github_token}"
            }

    def _get_cache_key(self, method: str, repo_name: str = "", extra: str = "") -> str:
        """Generate cache key for method calls"""
        return f"{method}:{repo_name}:{extra}"

    def _get_cached_data(self, cache_key: str, use_file_cache: bool = False):
        """Get data from cache if not expired"""
        cache = self._file_cache if use_file_cache else self._cache
        if cache_key in cache and not cache[cache_key].is_expired():
            return cache[cache_key].data
        return None

    def _set_cache_data(self, cache_key: str, data, expiry_minutes: int = 30, use_file_cache: bool = False):
        """Set data in cache"""
        cache = self._file_cache if use_file_cache else self._cache
        cache[cache_key] = CacheEntry(data, expiry_minutes)

    async def get_repositories(self) -> List[str]:
        cache_key = self._get_cache_key("repositories")
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        headers = await self.header()
        params = {
            "per_page": 100,
            "page": 1
        }
        repositories = []
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                while True:
                    r = await client.get(f"/orgs/{self.settings.github_org}/repos", params=params)
                    r.raise_for_status()
                    repos = r.json()
                    if not repos:
                        break
                    repositories.extend(repos)
                    params["page"] += 1

                repo_names = [repo["name"] for repo in repositories]
                self._set_cache_data(cache_key, repo_names, 60)  # Cache for 1 hour
                return repo_names
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def get_repository_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """Get file content with caching"""
        cache_key = self._get_cache_key("file_content", repo_name, file_path)
        cached_data = self._get_cached_data(cache_key, use_file_cache=True)
        if cached_data is not None:
            return cached_data

        headers = await self.header()
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contents/{file_path}")
                if r.status_code == 404:
                    self._set_cache_data(cache_key, None, 30, use_file_cache=True)
                    return None

                r.raise_for_status()
                response_data = r.json()
                if "content" not in response_data:
                    self._set_cache_data(cache_key, None, 30, use_file_cache=True)
                    return None

                content_bytes = base64.b64decode(response_data["content"])
                content_str = content_bytes.decode("utf-8")
                self._set_cache_data(cache_key, content_str, 30, use_file_cache=True)
                return content_str
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self._set_cache_data(cache_key, None, 30, use_file_cache=True)
                return None
            raise HTTPException(e.response.status_code, e.response.text)

    async def get_repository_contributors(self, repo_name: str) -> List[str]:
        cache_key = self._get_cache_key("contributors", repo_name)
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        headers = await self.header()
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contributors")
                if r.status_code in [404, 204]:
                    self._set_cache_data(cache_key, [], 30)
                    return []

                r.raise_for_status()
                contributors = [contributor["login"] for contributor in r.json()]
                self._set_cache_data(cache_key, contributors, 30)
                return contributors
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [404, 204]:
                self._set_cache_data(cache_key, [], 30)
                return []
            raise HTTPException(e.response.status_code, e.response.text)

    async def have_github_actions(self, repo_name: str) -> bool:
        cache_key = self._get_cache_key("github_actions", repo_name)
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        headers = await self.header()
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/actions/runs")
                if r.status_code == 404:
                    raise HTTPException(404, f"Repository {repo_name} not found")

                r.raise_for_status()
                have_actions_running = r.json()["total_count"] > 0
                self._set_cache_data(cache_key, have_actions_running, 30)
                return have_actions_running
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def check_repository_files_batch(self, repo_name: str) -> Dict[str, bool]:
        """
        Consolidated method to check multiple files at once and reduce API calls
        Returns dictionary with file checks results
        """
        cache_key = self._get_cache_key("files_batch", repo_name)
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        # Files to check
        files_to_check = [
            "mkdocs.yml",
            "mkdocs.yaml",
            "catalog-info.yaml",
            "catalog-info.yml"
        ]

        # Use asyncio.gather to make concurrent requests
        tasks = [self.get_repository_file_content(repo_name, file_path) for file_path in files_to_check]
        file_contents = await asyncio.gather(*tasks, return_exceptions=True)

        results = {
            "have_tech_docs": False,
            "have_github_actions_annotations": False,
            "have_datadog": False,
            "catalog_content": None
        }

        # Check mkdocs files - handle exceptions
        mkdocs_yml = file_contents[0] if not isinstance(file_contents[0], Exception) else None
        mkdocs_yaml = file_contents[1] if not isinstance(file_contents[1], Exception) else None

        if mkdocs_yml is not None or mkdocs_yaml is not None:
            results["have_tech_docs"] = True

        # Check catalog-info files and analyze content - handle exceptions
        catalog_yaml = file_contents[2] if not isinstance(file_contents[2], Exception) else None
        catalog_yml = file_contents[3] if not isinstance(file_contents[3], Exception) else None
        catalog_content = catalog_yaml if catalog_yaml is not None else catalog_yml

        if catalog_content and isinstance(catalog_content, str):
            results["catalog_content"] = catalog_content

            if "github.com/project-slug" in catalog_content:
                results["have_github_actions_annotations"] = True

            if "datadoghq.com/graph-token" in catalog_content:
                results["have_datadog"] = True
        self._set_cache_data(cache_key, results, 30)
        return results

    async def have_tech_docs(self, repo_name: str) -> bool:
        """Optimized version using batch file checking"""
        files_info = await self.check_repository_files_batch(repo_name)
        return files_info["have_tech_docs"]

    async def have_sonar(self, repo_name: str) -> bool:
        """
        Optimized sonar check using code search API more efficiently
        """
        cache_key = self._get_cache_key("sonar", repo_name)
        cached_data = self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data
        headers = await self.header()
        try:
            async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=10) as client:
                # Combine both queries in a single search with OR operator
                query = f'repo:{self.settings.github_org}/{repo_name} ("sonarqube.org/project-key" OR "sonarqube.org/organization-key") in:file'
                r = await client.get(f"/search/code", params={"q": query})
                r.raise_for_status()

                response_data = r.json()
                total_count = response_data.get("total_count", 0)
                has_sonar = total_count > 0

                self._set_cache_data(cache_key, has_sonar, 30)
                return has_sonar
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error: {e}")

    async def have_github_actions_annotations(self, repo_name: str) -> bool:
        """Optimized version using batch file checking"""
        files_info = await self.check_repository_files_batch(repo_name)
        return files_info["have_github_actions_annotations"]

    async def have_datadog(self, repo_name: str) -> bool:
        """Optimized version using batch file checking"""
        files_info = await self.check_repository_files_batch(repo_name)
        return files_info["have_datadog"]

    async def get_repository_complete_info(self, repo_name: str) -> Dict:
        """
        Get all repository information with minimal API calls
        This method consolidates multiple checks into fewer API calls
        """
        # Use asyncio.gather to make concurrent requests
        tasks = [
            self.get_repository_contributors(repo_name),
            self.have_github_actions(repo_name),
            self.check_repository_files_batch(repo_name),
            self.have_sonar(repo_name)
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results individually
            contributors = results[0] if not isinstance(results[0], Exception) else []
            have_actions = results[1] if not isinstance(results[1], Exception) else False
            default_files_info = {
                "have_tech_docs": False,
                "have_github_actions_annotations": False,
                "have_datadog": False
            }
            files_info = results[2] if not isinstance(results[2], Exception) else default_files_info
            have_sonar = results[3] if not isinstance(results[3], Exception) else False

            final_result = {
                "contributors": contributors,
                "have_github_actions": have_actions,
                "have_tech_docs": files_info.get("have_tech_docs", False) if isinstance(files_info, dict) else False,
                "have_github_actions_annotations": files_info.get("have_github_actions_annotations", False) if isinstance(files_info, dict) else False,
                "have_datadog": files_info.get("have_datadog", False) if isinstance(files_info, dict) else False,
                "have_sonar": have_sonar
            }

            return final_result

        except Exception as e:
            # Return default values if there's an error
            return {
                "contributors": [],
                "have_github_actions": False,
                "have_tech_docs": False,
                "have_github_actions_annotations": False,
                "have_datadog": False,
                "have_sonar": False
            }

    async def get_multiple_repositories_info(self, repo_names: List[str], max_concurrent: int = 5) -> Dict[str, Dict]:
        """
        Get information for multiple repositories with controlled concurrency
        to avoid overwhelming the API
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_repo_info_with_semaphore(repo_name: str):
            async with semaphore:
                return repo_name, await self.get_repository_complete_info(repo_name)

        tasks = [get_repo_info_with_semaphore(repo_name) for repo_name in repo_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        repo_info_dict = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, tuple) and len(result) == 2:
                repo_name, info = result
                repo_info_dict[repo_name] = info

        return repo_info_dict

    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._file_cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        total_entries = len(self._cache) + len(self._file_cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
        expired_entries += sum(1 for entry in self._file_cache.values() if entry.is_expired())
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "cache_entries": len(self._cache),
            "file_cache_entries": len(self._file_cache)
        }

    async def get_rate_limit_info(self) -> Dict:
        """Get GitHub API rate limit information"""
        if self.settings.use_github_app:
            github_app = await self._get_github_app_auth()
            return await github_app.get_rate_limit_info()
        else:
            headers = await self.header()
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

    async def get_auth_info(self) -> Dict:
        """Get authentication information"""
        if self.settings.use_github_app:
            github_app = await self._get_github_app_auth()
            auth_info = github_app.get_auth_info()
            auth_info["auth_type"] = "github_app"
        else:
            auth_info = {
                "auth_type": "token",
                "token_configured": bool(self.settings.github_token)
            }
        
        return auth_info