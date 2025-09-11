from ..schemas.settings import Settings
from ..modules.github import GithubClient
from ..modules.backstage import Backstage
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..schemas import sync_response, repository
import asyncio
from typing import List, Dict, cast


class GithubCommands(GithubClient, Backstage):
    settings: Settings = Settings()

    def __init__(self):
        super().__init__()
        self.db_collection = self.settings.mongo_collection_name

    async def get_all(
        self,
        db: AsyncIOMotorDatabase
    ) -> repository.RepositoryCollection:
        collection = db[self.db_collection]
        cursor = collection.find()
        repositorios = await cursor.to_list(length=1000)
        return repository.RepositoryCollection(repositories=repositorios, count=len(repositorios))

    async def get_all_name_repositories(
        self,
        db: AsyncIOMotorDatabase
    ) -> List[str]:
        collection = db[self.db_collection]
        cursor = collection.find({}, {"name": 1, "_id": 0})
        repositorios = await cursor.to_list(length=1000)
        return [repo["name"] for repo in repositorios]

    async def sync_repositories(
        self,
        db: AsyncIOMotorDatabase,
        batch_size: int = 10
    ) -> sync_response.SyncRepository:
        """
        Versión optimizada del sync que reduce drásticamente las llamadas a la API
        """
        from ..modules.sonarcloud import SonarCloudChecker

        collection = db[self.db_collection]


        # Obtener repositorios de forma concurrente
        repositories_in_db_task = self.get_all_name_repositories(db)
        repositories_in_github_task = self.get_repositories()
        backstage_repos_task = self.backstage_get_repositories()

        results = await asyncio.gather(
            repositories_in_db_task,
            repositories_in_github_task,
            backstage_repos_task,
            return_exceptions=True
        )

        # Manejar posibles errores en las tareas concurrentes
        repositories_in_db: List[str] = []
        repositories_in_github: List[str] = []
        backstage_repos: List[str] = []

        if not isinstance(results[0], Exception):
            repositories_in_db = cast(List[str], results[0])
        else:
            pass  # Error handled silently

        if not isinstance(results[1], Exception):
            repositories_in_github = cast(List[str], results[1])
        else:
            pass  # Error handled silently

        if not isinstance(results[2], Exception):
            backstage_repos = cast(List[str], results[2])
        else:
            pass  # Error handled silently

        new_repos = [item for item in repositories_in_github if item not in repositories_in_db]
        delete_repos = [item for item in repositories_in_db if item not in repositories_in_github]

        # Configurar SonarCloud
        sonarcloud_token = getattr(self.settings, "sonarcloud_token", None)
        sonarcloud_org = getattr(self.settings, "sonarcloud_org", None)
        sonar_checker = SonarCloudChecker(token=sonarcloud_token) if sonarcloud_token else None

        if not new_repos and not delete_repos:

            return sync_response.SyncRepository(
                status="No changes",
                newRepositories=[],
                deletedRepositories=[],
                newRepositoriesCount=0,
                deletedRepositoriesCount=0
            )

        # Eliminar repositorios obsoletos
        if delete_repos:
            for repo in delete_repos:
                await collection.delete_one({"name": repo})

        # Procesar repositorios nuevos en lotes para evitar rate limiting
        if new_repos:
            for i in range(0, len(new_repos), batch_size):
                batch = new_repos[i:i + batch_size]

                await self._process_repositories_batch(
                    batch,
                    backstage_repos,
                    sonar_checker,
                    sonarcloud_org or "",
                    collection
                )

                # Pequeña pausa entre lotes para ser más gentil con la API
                if i + batch_size < len(new_repos):
                    await asyncio.sleep(1)

        return sync_response.SyncRepository(
            status="Updated",
            newRepositories=new_repos,
            deletedRepositories=delete_repos,
            newRepositoriesCount=len(new_repos),
            deletedRepositoriesCount=len(delete_repos)
        )

    async def _process_repositories_batch(
        self,
        repo_batch: List[str],
        backstage_repos: List[str],
        sonar_checker,
        sonarcloud_org: str,
        collection
    ):
        """
        Procesa un lote de repositorios de forma optimizada
        """
        # Obtener toda la información de los repositorios de forma concurrente
        # Esto reduce las llamadas de ~7 por repo a ~4 por repo
        repo_info_dict = await self.get_multiple_repositories_info(repo_batch, max_concurrent=3)

        # Procesar la información de SonarCloud de forma concurrente si está disponible
        sonarcloud_tasks = []
        if sonar_checker and sonarcloud_org:
            for repo_name in repo_batch:
                task = self._check_sonarcloud_safe(sonar_checker, repo_name, sonarcloud_org)
                sonarcloud_tasks.append(task)

            sonarcloud_results = await asyncio.gather(*sonarcloud_tasks, return_exceptions=True)
        else:
            sonarcloud_results = [False] * len(repo_batch)

        # Crear documentos para insertar en la base de datos
        documents_to_insert = []

        for idx, repo_name in enumerate(repo_batch):
            repo_info = repo_info_dict.get(repo_name, {})

            # Verificar si está activo en Backstage
            active_backstage = repo_name in backstage_repos

            # Obtener resultado de SonarCloud
            sonar_result = sonarcloud_results[idx] if idx < len(sonarcloud_results) else False
            has_sonarcloud: bool = bool(sonar_result) if not isinstance(sonar_result, Exception) else False

            # Crear el documento del repositorio
            new_repo = repository.RepositoryInDB(
                name=repo_name,
                contributors=repo_info.get("contributors", []),
                backstage=repository.Backstage(
                    active=active_backstage,
                    tech_docs=repo_info.get("have_tech_docs", False),
                    sonar=repo_info.get("have_sonar", False),
                    github_actions=repo_info.get("have_github_actions_annotations", False),
                    datadog=repo_info.get("have_datadog", False)
                ),
                github=repository.Github(
                    active=repo_info.get("have_github_actions", False)
                ),
                sonarcloud=repository.SonarCloudInfo(active=has_sonarcloud)
            ).model_dump(by_alias=True, exclude={"id"})

            documents_to_insert.append(new_repo)

        # Insertar todos los documentos de una vez (bulk insert)
        if documents_to_insert:
            await collection.insert_many(documents_to_insert)

    async def _check_sonarcloud_safe(self, sonar_checker, repo_name: str, sonarcloud_org: str) -> bool:
        """
        Verificación segura de SonarCloud que maneja excepciones
        """
        try:
            return sonar_checker.has_sonarcloud(repo_name=repo_name, organization=sonarcloud_org)
        except Exception as e:
            return False

    async def validate_backstage(self):
        """
        Método para pruebas - mantiene compatibilidad
        """
        repos_backstage = await self.backstage_get_repositories()
        return repos_backstage

    async def get_cache_statistics(self) -> Dict:
        """
        Obtiene estadísticas del cache para monitoreo
        """
        return self.get_cache_stats()

    async def clear_repository_cache(self):
        """
        Limpia el cache - útil para testing o cuando se necesite forzar actualizaciones
        """
        self.clear_cache()
        return {"status": "Cache cleared successfully"}

    async def sync_single_repository(
        self,
        db: AsyncIOMotorDatabase,
        repo_name: str
    ) -> Dict:
        """
        Sincroniza un solo repositorio - útil para actualizaciones específicas
        """
        from ..modules.sonarcloud import SonarCloudChecker

        collection = db[self.db_collection]

        # Verificar si el repositorio existe en GitHub
        github_repos = await self.get_repositories()
        if repo_name not in github_repos:
            return {"status": "error", "message": f"Repository {repo_name} not found in GitHub"}

        # Obtener información del repositorio
        repo_info = await self.get_repository_complete_info(repo_name)

        # Obtener información de Backstage
        backstage_repos = await self.backstage_get_repositories()
        active_backstage = repo_name in backstage_repos

        # Verificar SonarCloud
        sonarcloud_token = getattr(self.settings, "sonarcloud_token", None)
        sonarcloud_org = getattr(self.settings, "sonarcloud_org", None)
        has_sonarcloud = False

        if sonarcloud_token and sonarcloud_org:
            sonar_checker = SonarCloudChecker(token=sonarcloud_token)
            has_sonarcloud = await self._check_sonarcloud_safe(sonar_checker, repo_name, sonarcloud_org)

        # Crear documento del repositorio
        repo_document = repository.RepositoryInDB(
            name=repo_name,
            contributors=repo_info.get("contributors", []),
            backstage=repository.Backstage(
                active=active_backstage,
                tech_docs=repo_info.get("have_tech_docs", False),
                sonar=repo_info.get("have_sonar", False),
                github_actions=repo_info.get("have_github_actions_annotations", False),
                datadog=repo_info.get("have_datadog", False)
            ),
            github=repository.Github(
                active=repo_info.get("have_github_actions", False)
            ),
            sonarcloud=repository.SonarCloudInfo(active=has_sonarcloud)
        ).model_dump(by_alias=True, exclude={"id"})

        # Actualizar o insertar en la base de datos
        result = await collection.replace_one(
            {"name": repo_name},
            repo_document,
            upsert=True
        )

        if result.upserted_id:
            return {"status": "created", "message": f"Repository {repo_name} created successfully"}
        else:
            return {"status": "updated", "message": f"Repository {repo_name} updated successfully"}