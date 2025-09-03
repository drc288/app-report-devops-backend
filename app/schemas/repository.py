from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

from ..modules.pyobject_mongo import PyObjectId

class Github(BaseModel):
    active: Optional[bool] = None
    github_flow: Optional[bool] = None

class Backstage(BaseModel):
    active: Optional[bool] = None
    tech_docs: Optional[bool] = None
    sonar: Optional[bool] = None
    datadog: Optional[bool] = None
    github_actions: Optional[bool] = None

class RepositoryBase(BaseModel):
    """
    Repository schema for MongoDB
    """
    name: str
    contributors: Optional[list[str]]
    backstage: Optional[Backstage]
    github: Optional[Github]

class RepositoryInDB(RepositoryBase):
    """
    Repository schema for MongoDB, como se almacenara el objeto en la base de datos
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Repository(RepositoryBase):
    id: str = Field(..., alias="_id")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class RepositoryCollection(BaseModel):
    count: int
    repositories: list[RepositoryInDB]
