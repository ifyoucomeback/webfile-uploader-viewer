"""客户端启动入口，支持脚本运行和包导入。"""

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from client.web import create_app
else:
    from .web import create_app
app = create_app()
if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="0.0.0.0", port=5210)
    except KeyboardInterrupt:
        pass
