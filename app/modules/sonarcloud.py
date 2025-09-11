import requests
from typing import Optional

class SonarCloudChecker:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://sonarcloud.io/api/projects/search"

    def has_sonarcloud(self, repo_name: str, organization: Optional[str] = None) -> bool:
        """
        Verifica si el repositorio existe en SonarCloud usando la API.
        :param repo_name: Nombre del repositorio/proyecto en SonarCloud
        :param organization: (Opcional) Nombre de la organización en SonarCloud
        :return: True si el proyecto existe, False si no
        """
        params = {"q": repo_name}
        if organization:
            params["organization"] = organization
        response = requests.get(
            self.base_url,
            params=params,
            auth=(self.token, "")
        )
        if response.status_code == 200:
            data = response.json()
            for project in data.get("components", []):
                if project.get("key") == repo_name or project.get("name") == repo_name:
                    return True
            return False
        else:
            response.raise_for_status()
            return False
