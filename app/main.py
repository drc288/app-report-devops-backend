from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import github
from .db.mongo import mongodb
from .schemas.settings import Settings
from .modules.github import GithubClient  # agregado

app = FastAPI()
settings = Settings()

cors = settings.cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await mongodb.connect()

@app.on_event("shutdown")
async def shutdown():
    await mongodb.close()

app.include_router(github.router)

