from ..schemas.settings import Settings
import httpx
from fastapi import HTTPException
import base64


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
        print(repo_name)
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contributors")
                if r.status_code in [404, 204]:
                    return []
                contributors = [contributor["login"] for contributor in r.json()]
                return contributors
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def have_github_actions(self, repo_name) -> bool:
        headers = self.header()
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/actions/runs")
                if r.status_code == 404:
                    raise HTTPException(404, f"Repository {repo_name} not found")
                have_actions_running = r.json()["total_count"] > 0
                return have_actions_running
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def have_tech_docs(self, repo_name: str) -> bool:
        headers = self.header()
        filenames = ["mkdocs.yml", "mkdocs.yaml"]
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                for filename in filenames:
                    r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contents/{filename}")
                    if r.status_code == 200:
                        return True
                    elif r.status_code != 404:
                        r.raise_for_status()
                return False
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error: {e}")

    async def have_sonar(self, repo_name: str) -> bool:
        headers = self.header()
        try:
            async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=10) as client:
                query = f'repo:{self.settings.github_org}/{repo_name} "sonarqube.org/project-key" in:file'
                r = await client.get(f"/search/code", params={"q": query})
                r.raise_for_status()
                if r.json().get("total_count", 0) > 0:
                    return True

                query2 = f'repo:{self.settings.github_org}/{repo_name} "sonarqube.org/organization-key" in:file'
                r2 = await client.get(f"/search/code", params={"q": query2})
                r2.raise_for_status()
                return r2.json().get("total_count", 0) > 0
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error: {e}")

    async def have_github_actions_annotations(self, repo_name: str) -> bool:
        headers = self.header()
        filenames = ["catalog-info.yaml", "catalog-info.yml"]
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                for filename in filenames:
                    r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contents/{filename}")
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()

                    content_bytes = base64.b64decode(r.json()["content"])
                    content_str = content_bytes.decode("utf-8")

                    if "github.com/project-slug" in content_str:
                        return True
                return False
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error: {e}")

    async def have_datadog(self, repo_name: str) -> bool:
        headers = self.header()
        filenames = ["catalog-info.yaml", "catalog-info.yml"]
        try:
            async with httpx.AsyncClient(base_url=self.api_url, headers=headers, timeout=10) as client:
                for filename in filenames:
                    r = await client.get(f"/repos/{self.settings.github_org}/{repo_name}/contents/{filename}")
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()

                    content_bytes = base64.b64decode(r.json()["content"])
                    content_str = content_bytes.decode("utf-8")

                    if "datadoghq.com/graph-token" in content_str:
                        return True
                return False
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
        except Exception as e:
            raise HTTPException(500, f"Unexpected error: {e}")
