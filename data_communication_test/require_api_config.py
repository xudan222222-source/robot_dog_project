import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "api_config.json"

with CONFIG_PATH.open("r", encoding="utf-8") as file:
    API_CONFIG = json.load(file)


def get_api_config(api_name: str) -> dict:
    api = API_CONFIG["apis"].get(api_name)

    if api is None:
        raise KeyError(f"未找到接口配置：{api_name}")

    if not api.get("path"):
        raise ValueError(f"接口路径尚未配置：{api_name}")

    return api
