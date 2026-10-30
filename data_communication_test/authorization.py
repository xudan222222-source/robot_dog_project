import json
import http.client
from pathlib import Path
from config import BACKEND_URL2, APPID
from data_communication_test.require_api_config import get_api_config

CONFIG_PATH = Path(__file__).resolve().parent / "api_config.json"

with CONFIG_PATH.open("r", encoding="utf-8") as file:
    API_CONFIG = json.load(file)


def get_authorization_token()->str:
    api_cfg = get_api_config("login")
    conn = http.client.HTTPSConnection(BACKEND_URL2)
    payload = json.dumps({
        "appId": APPID,
    })
    headers = {
        'Content-Type': 'application/json'
    }
    conn.request(api_cfg['method'], api_cfg['path'], payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()
    resp_text = data.decode("utf-8")
    status = res.status
    print(f"【login接口 status】{status}")
    # print(f"【login接口返回原始】{resp_text}")

    resp_json = json.loads(resp_text)
    # 增加业务成功判断
    if status == 200 and resp_json.get("success") is True:
        token = resp_json['data']['token']
        print("✅ 获取token成功")
        return token
    else:
        print("❌ login鉴权失败，无法获取token")
        # 返回空字符串，上层代码判断
        return ""
