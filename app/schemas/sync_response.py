from typing_extensions import List
from pydantic import BaseModel

class SyncRepository(BaseModel):
    status: str
    count: int
    repositories: List[str]