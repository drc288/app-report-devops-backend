from ..schemas.settings import Settings

import httpx
from fastapi import HTTPException



class GithubClient:
    settings: Settings
    api_url = "https://api.github.com"

    def __init__(self):
        pass

    def header(self):
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "fastapi-client",
            "Authorization": f"Bearer {self.settings.github_token}"
        }

    async def get_repositories(self) -> list[str]:
        headers = self.header()
        params = {
            "per_page": 100,
            "page": 1
        }
        repositories = []
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                while True:
                    r = await client.get(f"/orgs/{self.settings.github_org}/repos", params=params)
                    repos = r.json()
                    if not repos:
                        break
                    repositories.extend(repos)
                    params["page"] += 1
                return [repo["name"] for repo in repositories]
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def get_repository_contributors(self, repo_name) -> list[str]:
        headers = self.header()
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contributors")
                return [contributor["login"] for contributor in r.json()]
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
