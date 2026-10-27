"""服务端启动入口，支持脚本运行和包导入。"""

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    if __name__ == "server":
        # 兼容在 server 目录执行 uvicorn server:app 时的同名模块导入。
        __path__ = [str(Path(__file__).resolve().parent)]
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from server.application import create_app
else:
    from .application import create_app
app = create_app()
if __name__ == "__main__":
    import uvicorn

    config = app.state.services.config
    uvicorn.run(app, host=config["server"]["host"], port=int(config["server"]["port"]))
