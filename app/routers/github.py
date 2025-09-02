from functools import lru_cache
from pymongo.cursor import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..modules import github
from ..schemas import settings, sync_response, repository
from ..db.mongo import get_mongodb

dbCollection = "collection_repositories"

router = APIRouter(
    prefix="/github",
    tags=["github"],
    responses={404: {"description": "not found"}}
)

@lru_cache
def get_settings():
    return settings.Settings()

@router.get(
    "/",
    description="Get all repositories",
    status_code=status.HTTP_200_OK,
    response_model=List[str],
)
async def get_items(
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    repositoryCollection = db[dbCollection]
    cursor = repositoryCollection.find({}, {"name": 1, "_id": 0})
    repositories = await cursor.to_list(1000)
    return [repo["name"] for repo in repositories]

@router.post(
    "/sync",
    response_model=sync_response.SyncRepository,
    status_code=status.HTTP_201_CREATED,
    description="Sync repositories from GitHub"
)
async def sync_github(
    config: Annotated[settings.Settings, Depends(get_settings)],
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    repositoryCollection = db[dbCollection]

    repos = await github.get_repos(config.github_org, config.github_token)
    for repo in repos:
        newRepository = repository.RepositoryInDB(
            name=repo,
            contributors=[],
            backstage=None,
            github=None
        ).model_dump(by_alias=True, exclude=["id"])
        result = await repositoryCollection.insert_one(newRepository)
        newRepository["_id"] = result.inserted_id
        print(newRepository)

    returnRepos = sync_response.SyncRepository(
        status="complete",
        count=len(repos),
        repositories=repos
    )
    return returnRepos

@router.get("/{repositorio}")
async def get_repository(repositorio: str):
    return {f"{repositorio}": "Activo"}
