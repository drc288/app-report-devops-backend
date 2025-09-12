from fastapi import APIRouter, status, Response
from ..db.mongo import mongodb
from ..modules.github_app import GitHubAppAuth
from ..schemas.settings import Settings
from pathlib import Path

from datetime import datetime, timezone

router = APIRouter(
    prefix="/health",
    tags=["health"]
)

@router.get("/")
async def health_check(response: Response):
    """Health check endpoint validating MongoDB and GitHub App"""
    health_status = {
        "status": "healthy",
        "services": {
            "mongodb": {"status": "unknown"},
            "github_app": {"status": "unknown"}
        },
        "timestamp": None
    }
    health_status["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Check MongoDB
    try:
        if mongodb.client is not None:
            db = mongodb.get_db()
            if db is not None:
                await db.list_collection_names()
                health_status["services"]["mongodb"]["status"] = "healthy"
            else:
                raise Exception("Database connection not available")
        else:
            raise Exception("MongoDB client not initialized")
    except Exception as e:
        health_status["services"]["mongodb"]["status"] = "unhealthy"
        health_status["services"]["mongodb"]["error"] = str(e)
        health_status["status"] = "unhealthy"

    # Check GitHub App
    try:
        settings = Settings()

        if settings.use_github_app:
            # Check private key file exists
            key_path = Path(settings.github_app_private_key_path)
            if not key_path.exists():
                raise Exception("Private key file not found")

            # Test GitHub App authentication
            github_app = GitHubAppAuth(
                app_id=settings.github_app_id,
                private_key_path=settings.github_app_private_key_path,
                installation_id=settings.github_app_installation_id or None
            )

            # Try to get installation token (this validates the whole chain)
            await github_app.get_installation_token()
            health_status["services"]["github_app"]["status"] = "healthy"
            health_status["services"]["github_app"]["auth_type"] = "github_app"
        else:
            # Using token authentication
            if hasattr(settings, 'github_token') and settings.github_token:
                health_status["services"]["github_app"]["status"] = "healthy"
                health_status["services"]["github_app"]["auth_type"] = "token"
            else:
                raise Exception("No GitHub authentication configured")
    except Exception as e:
        health_status["services"]["github_app"]["status"] = "unhealthy"
        health_status["services"]["github_app"]["error"] = str(e)
        health_status["status"] = "unhealthy"

    # Set appropriate HTTP status code
    if health_status["status"] == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status