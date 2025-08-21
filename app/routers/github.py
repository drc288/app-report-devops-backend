from functools import lru_cache
from fastapi import APIRouter, Depends
from typing_extensions import Annotated

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
async def get_items(config: Annotated[settings.Settings, Depends(get_settings)]):
    return {"status": f"{config.github_org}"}

@router.post("/sync/")
async def sync_github():
    return {"status": "complete"}

@router.get("/{repositorio}")
async def get_repository(repositorio: str):
    return {f"{repositorio}": "Activo"}
