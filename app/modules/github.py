import httpx
from fastapi import HTTPException

apiUrl = "https://api.github.com"

async def get_repos(organization: str, token: str):
  headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "fastapi-clien",
        "Authorization": f"Bearer {token}"
    }
  params = {"per_page": 100, "page": 1}
  repositories = []
  try:
    async with httpx.AsyncClient(base_url=apiUrl, headers=headers, timeout=10) as client:
      while True:
        r = await client.get(f"/orgs/{organization}/repos", params=params)
        repos = r.json()
        if not repos:
          break
        repositories.extend(repos)
        params["page"] += 1
      return [repo["name"] for repo in repositories]
  except httpx.HTTPStatusError as e:
    raise HTTPException(e.response.status_code, e.response.text)
