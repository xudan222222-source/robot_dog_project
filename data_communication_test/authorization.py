import json
import http.client
from pathlib import Path
from config import BACKEND_URL, APPID
from require_api_config import get_api_config

CONFIG_PATH = Path(__file__).resolve().parent / "api_config.json"

with CONFIG_PATH.open("r", encoding="utf-8") as file:
    API_CONFIG = json.load(file)


def get_authorization_token()->str:
    # 只调用一次获取授权接口配置
    api_cfg = get_api_config("login")

    conn = http.client.HTTPSConnection(BACKEND_URL)

    # con.request()要求body必须为bytes或str
    payload = json.dumps({
        "appId": APPID,
    })
    headers = {
        'Content-Type': 'application/json'
    }

    conn.request(api_cfg['method'], api_cfg['path'], payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()  # 关闭连接

    # bytes转字符串
    resp_text = data.decode("utf-8")
    #res是字节(对象),对象的访问用.
    status = res.status

    # 新增：json字符串转字典
    resp_json = json.loads(resp_text)
    # 提取token，这里key名字按你后端实际返回改，我这里示例是 "token"
    token = resp_json['data']['token']
    return token
