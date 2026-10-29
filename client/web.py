"""客户端 Web 应用装配与静态资源。"""

from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from shared.assets import STATIC_DIRECTORY

from .application import ClientApplication
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
    asset_versions = {}
    for prefix, directory in (
        ("/static/", BASE_DIR / "static"),
        ("/file-browser-assets/", STATIC_DIRECTORY),
    ):
        for path in directory.rglob("*"):
            if path.is_file():
                url = prefix + path.relative_to(directory).as_posix()
                asset_versions[url] = sha256(path.read_bytes()).hexdigest()[:12]

    def asset_url(url):
        return f"{url}?v={asset_versions[url]}"

    templates.env.globals["asset_url"] = asset_url

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

    def render_page(request, template, page, title):
        return templates.TemplateResponse(
            request=request,
            name=template,
            context={"page": page, "page_title": title},
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return render_page(request, "index.html", "uploads", "正在上传")

    @app.get("/queue", response_class=HTMLResponse)
    async def queue_page(request: Request):
        return render_page(request, "queue.html", "queue", "上传队列")

    @app.get("/files", response_class=HTMLResponse)
    async def files_page(request: Request):
        return render_page(request, "files.html", "files", "本地文件浏览")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        return render_page(request, "settings.html", "settings", "设置")

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
