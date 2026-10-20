import http.client
import json

import requests
from config import BACKEND_URL
from require_api_config import get_api_config
from authorization import get_authorization_token

class LightingControl:

    def lighting_control_http(self, robotic_sn: str):
        """调用后端灯光控制接口。"""

        api_cfg = get_api_config("light_control")
        token = get_authorization_token()
        # 新增校验
        if not token:
            return {
                "http_status": None,
                "error": "鉴权失败，token为空，跳过灯光接口请求"
            }

        url = (
            f"{BACKEND_URL.rstrip('/')}/"
            f"{api_cfg['path'].lstrip('/')}"
        )

        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}"
        }

        payload = {
            "roboticSn": robotic_sn,
            "lightType": "SEARCH",
            "lightSwitch": "CLOSE"
        }

        try:
            response = requests.request(
                method=api_cfg["method"],
                url=url,
                json=payload,
                headers=headers,
                timeout=10
            )

            try:
                body = response.json()
            except ValueError:
                body = response.text

            return {
                "http_status": response.status_code,
                "response": body
            }

        except requests.RequestException as exc:
            return {
                "http_status": None,
                "error": str(exc)
            }

    def lighting_control_MQTT(self):
        """灯光控制MQTT接口，直接复用self.robotic_sn"""
        # 后续写MQTT发布逻辑时，payload/topic直接使用 self.robotic_sn
        pass

if __name__ == "__main__":
        # 1. 先创建实例
        ctrl = LightingControl()
        # 2. 调用方法，传入需要的 robotic_sn 参数
        ctrl.lighting_control_http(robotic_sn="go2test1")
