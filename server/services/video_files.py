"""旧播放/下载接口沿用原始路径参数，并统一验证实际存储边界。"""

import os

from shared.file_http import file_http_error


def get_video_file(request, client_name, relative_path):
    services = request.app.state.services
    try:
        client_directory, target = services.uploads._build_target_path(
            client_name, relative_path
        )
        stored_path = os.path.relpath(target, client_directory).replace(os.sep, "/")
        return str(services.file_browser.resolve_file(client_name, stored_path))
    except (ValueError, OSError) as exc:
        raise file_http_error(exc) from exc
