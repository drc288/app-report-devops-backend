from ..schemas.settings import Settings
from ..modules.github import GithubClient
from ..modules.backstage import Backstage
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..schemas import sync_response, repository

class GithubCommands(GithubClient, Backstage):
    settings: Settings = Settings()

    def __init__(self):
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
    ) -> list[str]:
        collection = db[self.db_collection]
        cursor = collection.find({}, {"name": 1, "_id": 0})
        repositorios = await cursor.to_list(length=1000)
        return [repo["name"] for repo in repositorios]

    async def sync_repositories(
        self,
        db: AsyncIOMotorDatabase
    ) -> sync_response.SyncRepository:
        collection = db[self.db_collection]
        repositories_in_db = await self.get_all_name_repositories(db)
        repositories_in_github = await self.get_repositories()

        new_repos = [item for item in repositories_in_github if item not in repositories_in_db]
        delete_repos = [item for item in repositories_in_db if item not in repositories_in_github]
        backstage_repos = await self.backstage_get_repositories()

        if not new_repos and not delete_repos:
            return sync_response.SyncRepository(
                status="No changes",
                newRepositories=[],
                deletedRepositories=[],
                newRepositoriesCount=0,
                deletedRepositoriesCount=0
            )

        for repo in delete_repos:
            await collection.delete_one({"name": repo})

        for repo in new_repos:
            active_backsatge = repo in backstage_repos
            have_github_actions = await self.have_github_actions(repo)
            contributors = await self.get_repository_contributors(repo)
            new_repo = repository.RepositoryInDB(
                name=repo,
                contributors=contributors,
                backstage=repository.Backstage(
                    active=active_backsatge
                ),
                github=repository.Github(
                    active=have_github_actions
                ),
            ).model_dump(by_alias=True, exclude=["id"])
            await collection.insert_one(new_repo)

        return sync_response.SyncRepository(
            status="Updated",
            newRepositories=new_repos,
            deletedRepositories=delete_repos,
            newRepositoriesCount=len(new_repos),
            deletedRepositoriesCount=len(delete_repos)
        )

    # Metodo para pruebas
    async def validate_backstage(
        self
    ):
        # collection = db[self.db_collection]
        # repositories_in_db = await self.get_all_name_repositories(db)
        # repositories_in_github = await self.get_repositories()
        repos_backstage = self.backstage_get_repositories()
        return repos_backstage


