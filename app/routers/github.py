from functools import lru_cache
from fastapi import APIRouter, Depends
from typing_extensions import Annotated

from ..modules import github
from ..schemas import settings

router = APIRouter(
    prefix="/github",
    tags=["github"],
    responses={404: {"description": "not found"}}
)

@lru_cache
def get_settings():
    return settings.Settings()


@router.get("/")
async def get_items():
    return {"status": "yes"}

@router.get("/sync/")
async def sync_github(config: Annotated[settings.Settings, Depends(get_settings)]):
    repos = await github.get_repos(config.github_org, config.github_token)
    print(repos)
    return {"status": "complete"}

@router.get("/{repositorio}")
async def get_repository(repositorio: str):
    return {f"{repositorio}": "Activo"}
