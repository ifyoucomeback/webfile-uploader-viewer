"""客户端接口共用的运行实例依赖。"""

from fastapi import HTTPException


def local_browser(request):
    application = request.app.state.runtime.application
    if application is None:
        raise HTTPException(503, "客户端尚未启动")
    return application.local_files
