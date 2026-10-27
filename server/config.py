import copy
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_CONFIG = {
    "server": {"host": "0.0.0.0", "port": 5211},
    "storage": {
        "upload_directory": "/data/video_upload",
        "uploading_directory": "/data/video_upload/.uploading",
    },
    "dns": {"server": "10.136.0.253", "timeout": 5},
    "upload": {
        "chunk_size": 1048576,
        "max_file_size": 0,
        "incomplete_expire_days": 30,
        "min_free_space": 5368709120,
    },
    "auth": {"upload_psk": "", "web_users": [], "session_expire_hours": 12},
}


def _merge_config(default, current):
    """
    递归合并配置。

    current 中已经存在的值优先使用 current。
    default 中新增的配置项自动补进去。
    """
    if not isinstance(default, dict):
        return current
    if not isinstance(current, dict):
        return copy.deepcopy(default)
    result = copy.deepcopy(default)
    for key, value in current.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = copy.deepcopy(DEFAULT_CONFIG)
        save_config(config)
        return config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        current_config = json.load(f)
    config = _merge_config(DEFAULT_CONFIG, current_config)
    return config


def save_config(config):
    temporary_file = CONFIG_FILE + ".tmp"
    try:
        with open(temporary_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_file, CONFIG_FILE)
    finally:
        if os.path.exists(temporary_file):
            try:
                os.remove(temporary_file)
            except OSError:
                pass
