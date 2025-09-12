from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import github, health
from .db.mongo import mongodb
from .schemas.settings import Settings

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
app.include_router(health.router)

