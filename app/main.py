from fastapi import FastAPI

from .routers import github

app = FastAPI()

app.include_router(github.router)