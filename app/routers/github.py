from fastapi import APIRouter, Depends, status, Query
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

@router.post(
    "/sync",
    response_model=sync_response.SyncRepository,
    status_code=status.HTTP_201_CREATED,
    description="Sync repositories from GitHub (Optimized version with reduced API calls)"
)
async def sync_github(
    db: AsyncIOMotorDatabase = Depends(get_mongodb),
    batch_size: int = Query(default=10, ge=1, le=50, description="Number of repositories to process in each batch")
):
    """
    Sync repositories from GitHub to MongoDB using optimized API calls.

    This version significantly reduces the number of API calls to GitHub:
    - Uses caching to avoid repeated calls
    - Consolidates multiple file checks into single requests
    - Processes repositories in batches to respect rate limits
    - Uses concurrent requests where possible

    Args:
        batch_size: Number of repositories to process simultaneously (1-50)
    """
    return await github_commands.sync_repositories(db, batch_size)

@router.post(
    "/sync/{repository_name}",
    description="Sync a single repository (Optimized version)"
)
async def sync_single_repository(
    repository_name: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Sync a single repository from GitHub to MongoDB.

    This is useful for updating specific repositories without running a full sync.
    """
    result = await github_commands.sync_single_repository(db, repository_name)
    return result

@router.delete(
    "/cache",
    description="Clear all cache"
)
async def clear_cache():
    """
    Clear all cached data. Useful for testing or when you need to force fresh data.

    Note: This will cause the next sync to make fresh API calls to GitHub.
    """
    return await github_commands.clear_repository_cache()

@router.get(
    "/auth/info",
    description="Get GitHub authentication information"
)
async def get_auth_info():
    """
    Get information about current GitHub authentication method and status.
    """
    return await github_commands.get_auth_info()

@router.get(
    "/rate-limit",
    description="Get GitHub API rate limit information"
)
async def get_rate_limit_info():
    """
    Get current GitHub API rate limit status.
    Useful for monitoring API usage and avoiding rate limits.
    """
    return await github_commands.get_rate_limit_info()
