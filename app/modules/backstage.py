from ..schemas.settings import Settings

import httpx
from fastapi import HTTPException


class Backstage:
    settings: Settings

    def __init__(self):
        pass

    async def backstage_get_repositories(self) -> list[str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.settings.backstage_token}",
        }
        try:
            async with httpx.AsyncClient(base_url="https://cross-tools.palaceresorts.com", headers=headers, timeout=10) as client:
                r = await client.get("/backstage/api/catalog/locations")
                repositories_obj = r.json()
                # Obtiene la URL del repositorio agregado en backsatge
                repo_url = [repo["data"]["target"] for repo in repositories_obj]
                repositories_name = []
                for repo in repo_url:
                    # Obteniendo nombre del repositorio
                    repositories_name.append(repo.split("/")[4])
                return list(dict.fromkeys(repositories_name))
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

