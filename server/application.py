"""创建服务端应用；入口仅负责装配和生命周期。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shared.assets import STATIC_DIRECTORY

from .config import load_config
from .routes import (
    auth,
    clients,
    dashboard,
    downloads,
    file_actions,
    file_browser,
    file_downloads,
    file_preview,
    files,
    health,
    storage,
    streaming,
    uploads,
    users,
)
from .services.context import ServerServices

FRONTEND_DIRECTORY = Path(__file__).resolve().parent / "frontend"


def create_app(config=None):
    services = ServerServices.build(load_config() if config is None else config)

    @asynccontextmanager
    async def lifespan(app):
        try:
            await services.maintenance.start()
            yield
        finally:
            await services.maintenance.stop()

    app = FastAPI(title="Video Upload Server", lifespan=lifespan)
    app.state.services = services
    app.mount(
        "/file-browser-assets",
        StaticFiles(directory=STATIC_DIRECTORY),
        name="file-browser-assets",
    )
    app.mount(
        "/frontend",
        StaticFiles(directory=FRONTEND_DIRECTORY, html=True),
        name="frontend",
    )

    @app.get("/", include_in_schema=False)
    async def frontend_index():
        return FileResponse(FRONTEND_DIRECTORY / "index.html")

    for module in (
        auth,
        dashboard,
        files,
        file_browser,
        file_preview,
        file_downloads,
        file_actions,
        users,
        clients,
        storage,
        uploads,
        streaming,
        downloads,
        health,
    ):
        app.include_router(module.router)
    return app
