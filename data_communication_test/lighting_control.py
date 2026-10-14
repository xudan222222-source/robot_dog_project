import http.client
import json
from config import BACKEND_URL
from require_api_config import get_api_config
from authorization import get_authorization_token

class lighting_control:
    def lighting_control_http(self):
        roboticSn=''
        authorization=f"Bear {get_authorization_token()}"
        api_cfg = get_api_config("light_control")

        conn = http.client.HTTPSConnection(BACKEND_URL)


        payload = json.dumps({
           "roboticSn": roboticSn,
           "lightType": "SEARCH",
           "lightSwitch": "OPEN"
        })
        headers = {
            'Content-Type': 'application/json',
            'authorization': authorization
        }

        conn.request(api_cfg['method'], api_cfg['path'], payload, headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()

        status = res.status

        return status
    def lighting_control_MQTT(self):
        return
