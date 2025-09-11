from pymongo.cursor import List

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas import sync_response, repository
from ..db.mongo import get_mongodb
from ..db.github_commands import GithubCommands

router = APIRouter(
    prefix="/github",
    tags=["github"],
    responses={404: {"description": "not found"}}
)

github_commands = GithubCommands()

@router.get(
    "/",
    description="Get all repositories",
    status_code=status.HTTP_200_OK,
    response_model=repository.RepositoryCollection,
)
async def get_repositories(
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get all repositories from MongoDB.
    """
    return await github_commands.get_all(db)

@router.get(
    "/test"
)
async def test():
    return await github_commands.backstage_get_repositories()

@router.get(
    "/active-repositories",
    description="Get all repositories",
    status_code=status.HTTP_200_OK,
    response_model=List[str],
)
async def get_items(
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get all repositories from MongoDB.
    """
    return await github_commands.get_all_name_repositories(db)

@router.post(
    "/sync",
    response_model=sync_response.SyncRepository,
    status_code=status.HTTP_201_CREATED,
    description="Sync repositories from GitHub"
)
async def sync_github(
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Sync repositories from GitHub to MongoDB.
    """
    return await github_commands.sync_repositories(db)

@router.post(
    "/sync/{repositorio}",
)
async def get_repository(repositorio: str):
    return {f"{repositorio}": "Activo"}
