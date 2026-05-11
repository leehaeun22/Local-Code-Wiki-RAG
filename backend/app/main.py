from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.chat_router import router as chat_router
from app.routers.project_router import router as project_router
from app.routers.webhook_router import router as webhook_router



def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(project_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(webhook_router, prefix="/api/v1")

    return app


app = create_app()
