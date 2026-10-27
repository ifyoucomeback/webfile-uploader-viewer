import copy
import json
import os

from .upload_settings import DEFAULT_CONCURRENT_UPLOADS, validate_concurrency

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "server": {"host": "10.136.100.3", "port": 5211},
    "monitor": {
        "directories": [],
        "include_extensions": [".mp4", ".mkv", ".avi"],
        "exclude_extensions": [".tmp", ".part"],
        "interval": 600,
    },
    "upload": {
        "enabled": True,
        "max_bandwidth": 307200,
        "psk": "",
        "max_concurrent_uploads": DEFAULT_CONCURRENT_UPLOADS,
    },
}


def load_config():
    migrated = False
    if not os.path.exists(CONFIG_FILE):
        config = copy.deepcopy(DEFAULT_CONFIG)
        save_config(config)
        return config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    if not isinstance(config, dict):
        config = copy.deepcopy(DEFAULT_CONFIG)
        save_config(config)
        return config
    if "server" not in config:
        config["server"] = {}
        migrated = True
    if "host" not in config["server"]:
        config["server"]["host"] = DEFAULT_CONFIG["server"]["host"]
        migrated = True
    if "port" not in config["server"]:
        config["server"]["port"] = DEFAULT_CONFIG["server"]["port"]
        migrated = True
    if "monitor" not in config:
        config["monitor"] = {}
        migrated = True
    monitor = config["monitor"]
    if "directories" not in monitor:
        old_directory = monitor.get("directory", "")
        if isinstance(old_directory, str) and old_directory.strip():
            monitor["directories"] = [old_directory.strip()]
        else:
            monitor["directories"] = []
        migrated = True
    if "directory" in monitor:
        del monitor["directory"]
        migrated = True
    if not isinstance(monitor["directories"], list):
        monitor["directories"] = []
        migrated = True
    else:
        normalized_directories = []
        for directory in monitor["directories"]:
            if not isinstance(directory, str):
                continue
            directory = directory.strip()
            if not directory:
                continue
            if directory not in normalized_directories:
                normalized_directories.append(directory)
        if normalized_directories != monitor["directories"]:
            monitor["directories"] = normalized_directories
            migrated = True
    if "include_extensions" not in monitor:
        monitor["include_extensions"] = copy.deepcopy(
            DEFAULT_CONFIG["monitor"]["include_extensions"]
        )
        migrated = True
    if not isinstance(monitor["include_extensions"], list):
        monitor["include_extensions"] = copy.deepcopy(
            DEFAULT_CONFIG["monitor"]["include_extensions"]
        )
        migrated = True
    if "exclude_extensions" not in monitor:
        monitor["exclude_extensions"] = copy.deepcopy(
            DEFAULT_CONFIG["monitor"]["exclude_extensions"]
        )
        migrated = True
    if not isinstance(monitor["exclude_extensions"], list):
        monitor["exclude_extensions"] = copy.deepcopy(
            DEFAULT_CONFIG["monitor"]["exclude_extensions"]
        )
        migrated = True
    if "interval" not in monitor:
        monitor["interval"] = DEFAULT_CONFIG["monitor"]["interval"]
        migrated = True
    if "upload" not in config:
        config["upload"] = {}
        migrated = True
    upload = config["upload"]
    try:
        validate_concurrency(upload.get("max_concurrent_uploads"))
    except ValueError:
        upload["max_concurrent_uploads"] = DEFAULT_CONCURRENT_UPLOADS
        migrated = True
    if "enabled" not in upload:
        upload["enabled"] = DEFAULT_CONFIG["upload"]["enabled"]
        migrated = True
    if "max_bandwidth" not in upload:
        upload["max_bandwidth"] = DEFAULT_CONFIG["upload"]["max_bandwidth"]
        migrated = True
    if "psk" not in upload:
        upload["psk"] = DEFAULT_CONFIG["upload"]["psk"]
        migrated = True
    elif not isinstance(upload["psk"], str):
        upload["psk"] = ""
        migrated = True
    if migrated:
        save_config(config)
    return config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
