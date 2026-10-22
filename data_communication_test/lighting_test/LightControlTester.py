import json
import time
from pathlib import Path
import requests
from config import BACKEND_URL
from data_communication_test.require_api_config import get_api_config
from config import ROBOT_SN


CONFIG_PATH = Path(__file__).resolve().parent.parent / "api_config.json"
with CONFIG_PATH.open("r", encoding="utf-8") as file:
    API_CONFIG = json.load(file)


class LightControlTester:
    def __init__(self):
        pass

    def lighting_control_http(self, robotic_sn: str, light_type: str, light_switch: str, token: str):
        api_cfg = get_api_config("light_control")
        url = f"{BACKEND_URL}{api_cfg['path']}"

        payload = {
            "roboticSn": robotic_sn,
            "lightType": light_type,
            "lightSwitch": light_switch
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        # 调试打印，查看Bearer拼接是否正确
        # print("==== Authorization header ====")
        # print(repr(headers["Authorization"]))
        # print("==== 请求payload ====")
        # print(payload)

        resp = requests.request(
            method=api_cfg["method"],
            url=url,
            json=payload,
            headers=headers,
            timeout=10,
            verify=False
        )
        try:
            resp_json = resp.json()
        except Exception:
            resp_json = resp.text
        return {
            "http_status": resp.status_code,
            "response": resp_json
        }

    @staticmethod
    def _wait_log(ssh_client, keyword: str, timeout: int = 8, poll_interval: float = 0.02) -> bool:
        """等待日志出现关键词，ssh_client 是 BehaviorSshStream 对象"""
        log_path = "~/.ros/nlog/insp_doggo.log"
        cmd = f"tail -f {log_path}"
        stdin, stdout, stderr = ssh_client.stream_command(cmd, get_pty=True)
        start = time.time()
        try:
            while time.time() - start < timeout:
                line = stdout.readline()
                if line:
                    # line 已经是 str，不需要 decode
                    line_text = line
                    if keyword in line_text:
                        print(f"✅ 抓到目标日志：{line_text.strip()}")
                        return True
                else:
                    time.sleep(poll_interval)
            print(f"⏱ 超时，没有匹配到关键词：{keyword}")
            return False
        finally:
            stdin.close()

    def run_single_case(self, case: dict, behavior_ssh, token: str):
        print(f"\n--- 执行 case  lightType={case['lightType']}, lightSwitch={case['lightSwitch']} ---")
        ret = self.lighting_control_http(
            robotic_sn=ROBOT_SN,
            light_type=case["lightType"],
            light_switch=case["lightSwitch"],
            token=token
        )
        assert ret["http_status"] == 200, f"接口异常！result={ret}, payload={case}"
        print("✅ HTTP接口返回200，开始等待设备侧日志")
        ok = self._wait_log(behavior_ssh, keyword=case["expect_log_key"])
        assert ok, "❌ 未收到设备端预期日志"
        print("✅ 该用例校验通过\n")

    def get_case_list(self):
        light_api_cfg = API_CONFIG["apis"]["light_control"]
        return light_api_cfg.get("cases", [])

    def run_all_cases(self, behavior_ssh, token: str):
        case_list = self.get_case_list()
        for case in case_list:
            self.run_single_case(case, behavior_ssh, token)
        print("\n🎉 全部灯光用例执行完成！")


if __name__ == "__main__":
    ctrl = LightControlTester()
