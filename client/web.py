"""客户端 Web 应用装配与静态资源。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from shared.assets import STATIC_DIRECTORY

from .application import ClientApplication
from .client_info import get_client_info
from .config import load_config
from .routes import (
    config,
    file_actions,
    file_browser,
    file_downloads,
    file_preview,
    files,
    status,
    tasks,
)
from .runtime import ClientRuntime

BASE_DIR = Path(__file__).resolve().parent


def create_app(application_factory=ClientApplication, lock_file=None):
    runtime = ClientRuntime(application_factory, lock_file)
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @asynccontextmanager
    async def lifespan(app):
        try:
            await runtime.start()
            yield
        finally:
            await runtime.stop()

    app = FastAPI(title="Video Upload Client", lifespan=lifespan)
    app.state.runtime = runtime
    app.mount(
        "/file-browser-assets",
        StaticFiles(directory=STATIC_DIRECTORY),
        name="file-browser-assets",
    )
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        client = (
            runtime.application.client_info
            if runtime.application
            else get_client_info()
        )
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"config": load_config(), "client": client},
        )

    for module in (
        config,
        files,
        status,
        tasks,
        file_browser,
        file_preview,
        file_downloads,
        file_actions,
    ):
        app.include_router(module.router)
    return app
