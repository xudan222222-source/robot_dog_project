import shlex
from datetime import datetime
import paramiko
import time
from typing import Tuple

from config import (
    PUBLIC_SERVER_IP,
    # 背包
    BACKPACK_FRP_PORT,
    BACKPACK_USER,
    BACKPACK_PASSWORD,
    # 交换机下设备
    FOUR_IN_ONE_IP,
    FOUR_IN_ONE_PORT,
    GUN_IP,
    CAMERA_IP
)


class BackPackChecker:

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_password: str,
        four_in_one_ip: str,
        four_in_one_port: int,
        gun_ip: str,
        camera_ip: str,
        ssh_timeout: int = 50,
        ssh_retry_interval: int = 2
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password

        self.ssh_timeout = ssh_timeout
        self.ssh_retry_interval = ssh_retry_interval

        self.conn = None

        self.four_in_one_ip = four_in_one_ip
        self.four_in_one_port = four_in_one_port
        self.gun_ip = gun_ip
        self.camera_ip = camera_ip

    def connect_ssh(self) -> bool:
        start_time = time.time()

        while True:
            try:
                self.conn = paramiko.SSHClient()
                self.conn.set_missing_host_key_policy(
                    paramiko.AutoAddPolicy()
                )

                self.conn.connect(
                    hostname=self.ssh_host,
                    port=self.ssh_port,
                    username=self.ssh_user,
                    password=self.ssh_password,
                    timeout=10
                )

                return True

            except Exception as e:
                elapsed = time.time() - start_time

                if elapsed > self.ssh_timeout:
                    print(f"❌ SSH连接超时: {e}")
                    return False

                print(
                    f"SSH连接失败，重试中..."
                    f"({int(self.ssh_timeout - elapsed)}s剩余)"
                )

                time.sleep(self.ssh_retry_interval)

    def exec(
        self,
        cmd: str,
        timeout: int = 10
    ) -> Tuple[str, str]:

        full_cmd = (
            f"bash --login -c "
            f"{shlex.quote(cmd)}"
        )

        stdin, stdout, stderr = self.conn.exec_command(
            full_cmd,
            timeout=timeout + 2
        )

        out = stdout.read().decode(
            errors="ignore"
        ).strip()

        err = stderr.read().decode(
            errors="ignore"
        ).strip()

        return out, err

    def check_Speaker_device(self) -> Tuple[bool, str]:
        cmd = "aplay -l"

        out, err = self.exec(cmd)

        if out.strip():
            return True, f"Speaker已识别\n{out}"

        return False, out or err

    def check_Microphone_device(self) -> Tuple[bool, str]:
        cmd = "arecord -l | grep USB"

        out, err = self.exec(cmd)

        if out.strip():
            return True, f"Microphone已识别\n{out}"

        return False, out or err

    def ping_device(
        self,
        device_name: str,
        ip: str
    ) -> Tuple[bool, str]:

        cmd = f"ping -c 3 -W 2 {ip}"

        out, err = self.exec(cmd)
        #do test
        print(out)
        if "100% packet loss" in out:
            return False, (
                f"{device_name}({ip}) 网络异常\n"
                f"{out or err}"
            )
        return True, (
            f"{device_name}({ip}) 网络正常"
        )

    def check_telnet_port(
        self,
        device_name: str,
        ip: str,
        port: int
    ) -> Tuple[bool, str]:

        cmd = (
            f"timeout 5 telnet {ip} {port} "
            "</dev/null 2>&1"
        )

        out, err = self.exec(cmd)

        result = f"{out}\n{err}".lower()

        if (
            "connected to" in result
            or "escape character" in result
        ):
            return True, (
                f"{device_name}({ip}:{port}) "
                f"端口连接正常"
            )

        return False, (
            f"{device_name}({ip}:{port}) "
            f"端口连接失败\n"
            f"{out or err}"
        )

    def test_four_in_one(self):
        print("\n")
        print("=" * 60)
        print("                    四合一检测")
        print("=" * 60)

        print("\n[1] 四合一网络检测")

        four_ping_ok, four_ping_msg = self.ping_device(
            "四合一",
            self.four_in_one_ip
        )

        print(
            f"【四合一网络】: "
            f"{'OK' if four_ping_ok else 'FAIL'}"
        )

        if not four_ping_ok:
            print(four_ping_msg)
            print(
                "⚠️ 四合一网络异常，"
                "跳过端口检测"
            )

            return {
                "four_ping": False,
                "four_port": False
            }

        print("\n[2] 四合一端口检测")

        four_port_ok, four_port_msg = (
            self.check_telnet_port(
                "四合一",
                self.four_in_one_ip,
                self.four_in_one_port
            )
        )

        print(
            f"【四合一端口】: "
            f"{'OK' if four_port_ok else 'FAIL'}"
        )

        if not four_port_ok:
            print(four_port_msg)

        return {
            "four_ping": True,
            "four_port": four_port_ok
        }

    @staticmethod
    def get_timestamp():
        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def run_all_checks(self):

        timestamp_start = self.get_timestamp()

        print("\n")
        print("=" * 60)
        print("              背包测前检测")
        print("=" * 60)
        print(f"开始时间：{timestamp_start}")

        print("\n[1] SSH连接")
        print("⏳ 正在连接3588背包...")

        if not self.connect_ssh():
            print("❌ SSH连接失败，检测终止")
            return

        print("✅ SSH连接成功")

        print("\n[2] 音频设备检测")

        speaker_ok, speaker_msg = (
            self.check_Speaker_device()
        )

        print(
            f"【扬声器】: "
            f"{'OK' if speaker_ok else 'FAIL'}"
        )

        if not speaker_ok:
            print(speaker_msg)

        microphone_ok, microphone_msg = (
            self.check_Microphone_device()
        )

        print(
            f"【拾音器】: "
            f"{'OK' if microphone_ok else 'FAIL'}"
        )

        if not microphone_ok:
            print(microphone_msg)

        print("\n" + "!" * 60)
        print("⚠️ 注意：请先将摄像头开机！")
        print("!" * 60)

        input(
            "确认摄像头已经开机后，"
            "按 Enter 继续四合一检测..."
        )

        print("\n[3] 四合一检测")

        four_result = self.test_four_in_one()

        print("\n[4] 摄像头网络检测")

        camera_ok, camera_msg = self.ping_device(
            "摄像头",
            self.camera_ip
        )
        print("#############################")
        print(camera_ok)

        print(
            f"【摄像头】: "
            f"{'OK' if camera_ok else 'FAIL'}"
        )

        if not camera_ok:
            print(camera_msg)

        print("\n[5] 网枪网络检测")

        gun_ok, gun_msg = self.ping_device(
            "网枪",
            self.gun_ip
        )

        print(
            f"【网枪】: "
            f"{'OK' if gun_ok else 'FAIL'}"
        )

        if not gun_ok:
            print(gun_msg)

        print("\n[6] 背包测前检测结果")

        print("\n" + "=" * 60)

        print("【音频设备】")

        print(
            f"扬声器       : "
            f"{'PASS' if speaker_ok else 'FAIL'}"
        )

        print(
            f"拾音器       : "
            f"{'PASS' if microphone_ok else 'FAIL'}"
        )

        print("\n【四合一】")

        print(
            f"网络         : "
            f"{'PASS' if four_result['four_ping'] else 'FAIL'}"
        )

        print(
            f"端口         : "
            f"{'PASS' if four_result['four_port'] else 'FAIL'}"
        )

        print("\n【其他设备网络】")

        print(
            f"摄像头       : "
            f"{'PASS' if camera_ok else 'FAIL'}"
        )

        print(
            f"网枪         : "
            f"{'PASS' if gun_ok else 'FAIL'}"
        )

        all_ok = (
            speaker_ok
            and microphone_ok
            and four_result["four_ping"]
            and four_result["four_port"]
            and camera_ok
            and gun_ok
        )

        print("\n" + "=" * 60)

        if all_ok:
            print("✅ 背包测前检测完成：PASS")
        else:
            print("❌ 背包测前检测完成：FAIL")

        timestamp_end = self.get_timestamp()

        print(f"结束时间：{timestamp_end}")
        print("=" * 60)

        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    checker = BackPackChecker(
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=BACKPACK_FRP_PORT,
        ssh_user=BACKPACK_USER,
        ssh_password=BACKPACK_PASSWORD,
        four_in_one_ip=FOUR_IN_ONE_IP,
        four_in_one_port=FOUR_IN_ONE_PORT,
        gun_ip=GUN_IP,
        camera_ip=CAMERA_IP,
        ssh_timeout=50,
        ssh_retry_interval=2
    )

    checker.run_all_checks()
