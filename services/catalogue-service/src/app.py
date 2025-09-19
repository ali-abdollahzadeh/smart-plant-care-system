from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db_with_retry
from .routers import (
    health_controller as health,
    registry_controller as registry,
    plants_controller as plants,
    thresholds_controller as thresholds,
    alerts_controller as alerts,
    users,
    assignments,
    webhooks_controller as webhooks,
)

def create_app() -> FastAPI:
    app = FastAPI(title="Catalogue Service", version="1.0.0")

    # CORS allow all (per spec)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _on_startup() -> None:
        init_db_with_retry()

    # API per contract
    app.include_router(health.router)        # GET /health
    app.include_router(registry.router)      # /services/*
    app.include_router(plants.router)        # /plants/*
    app.include_router(thresholds.router)    # /thresholds/*
    app.include_router(alerts.router)        # /alerts/*
    app.include_router(users.router)         # /users/*
    app.include_router(assignments.router)   # /assignments/*
    app.include_router(webhooks.router)      # /webhooks/*

    @app.get("/version")
    def version():
        return {"version": "1.0.0"}

    return app

app = create_app()
