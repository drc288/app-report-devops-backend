from fastapi import FastAPI

from .routers import github
from .db.mongo import mongodb

app = FastAPI()

@app.on_event("startup")
async def startup():
    await mongodb.connect()

@app.on_event("shutdown")
async def shutdown():
    await mongodb.close()

app.include_router(github.router)