from typing_extensions import List
from pydantic import BaseModel

class SyncRepository(BaseModel):
    status: str
    newRepositories: List[str]
    newRepositoriesCount: int
    deletedRepositories: List[str]
    deletedRepositoriesCount: int