from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

from ..modules.pyobject_mongo import PyObjectId

class Github(BaseModel):
    active: bool
    github_flow: bool

class Backstage(BaseModel):
    active: bool
    tech_docs: bool
    sonar: bool
    datadog: bool
    github_actions: bool

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
