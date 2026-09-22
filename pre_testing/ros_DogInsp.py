import re
import shlex
from datetime import datetime
import paramiko
import time
from typing import Tuple

from config import (
    PUBLIC_SERVER_IP,
    # 狗端
    DOG_USER,
    DOG_PASSWORD,
    DOG_FRP_PORT
)


class DogChecker:

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_password: str,
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

        shell_cmd = (
            "source /home/unitree/unitree_ros2/setup.sh; "
            + cmd
        )

        full_cmd = (
            f"bash --login -c "
            f"{shlex.quote(shell_cmd)}"
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

    def ros2_echo_and_pub(
        self,
        topic: str,
        pub_cmd: str,
        expected_text: str,
        echo_timeout: int = 5
    ) -> Tuple[bool, str]:

        shell_cmd = (
            "source /home/unitree/unitree_ros2/setup.sh; "
            f"timeout {echo_timeout} "
            f"ros2 topic echo {topic}"
        )

        full_cmd = (
            f"bash --login -c "
            f"{shlex.quote(shell_cmd)}"
        )

        channel = (
            self.conn
            .get_transport()
            .open_session()
        )

        channel.exec_command(full_cmd)

        try:
            # 先让 echo 建立监听
            time.sleep(1)

            # 再发送 ROS2 指令
            pub_out, pub_err = self.exec(
                pub_cmd,
                timeout=10
            )

            if "publishing #1" not in pub_out:
                return False, (
                    "ROS2指令发送失败\n"
                    f"err:{pub_err}\n"
                    f"out:{pub_out}"
                )

            echo_content = ""

            start_time = time.time()

            while time.time() - start_time < echo_timeout:

                if channel.recv_ready():

                    data = channel.recv(4096)

                    echo_content += (
                        data.decode(
                            errors="ignore"
                        )
                    )

                    if expected_text in echo_content:
                        return True, (
                            "ROS2指令发送成功\n"
                            "echo监听成功\n"
                            f"echo内容:\n"
                            f"{echo_content}"
                        )

                if channel.exit_status_ready():
                    break

                time.sleep(0.2)

            return False, (
                "ROS2指令发送成功，"
                "但echo未捕获目标消息\n"
                f"期望内容:{expected_text}\n"
                f"echo内容:\n{echo_content}"
            )

        finally:
            if channel:
                channel.close()

    def check_imu(self) -> Tuple[bool, str]:
    #有部分小灰狗自买的imu名称为/imu_data_ros
        cmd = r"""
        timeout 5 ros2 topic echo /dog_imu_raw | head -n 50
        """

        out, err = self.exec(cmd)

        if (
            "orientation:" in out
            and "angular_velocity:" in out
            and "linear_acceleration:" in out
        ):
            return True, (
                "IMU 检查: 成功 - 数据存在"
            )

        return False, (
            "IMU 检查: 失败 - 数据缺失\n"
            f"{out}\n"
            f"{err}"
        )

    def check_rtk(self) -> Tuple[bool, str]:

        cmd = r"""
        timeout 5 ros2 topic echo /fix | head -n 50
        """

        out, err = self.exec(cmd)

        if not out.strip():
            return False, (
                "RTK 检查: 失败 - 无数据"
            )

        match = re.search(
            r"status:\s*\n\s*status:\s*(-?\d+)",
            out
        )

        if match:
            status_value = int(
                match.group(1)
            )
        else:
            status_value = None

        status_map = {
            2: "固定解 (精确导航)",
            1: "浮点解 (粗略可用)",
            0: "单点定位 (米级精度)",
            -1: "无定位",
        }

        if status_value in status_map:
            status_text = status_map[
                status_value
            ]
        else:
            status_text = (
                f"未知状态 ({status_value})"
            )

        return True, (
            f"RTK 检查: 成功 - "
            f"{status_text}"
        )

    def test_light_switch(self) -> Tuple[bool, str]:

        topic = "/light_control"

        cmd = r"""
        ros2 topic pub /light_control std_msgs/msg/String "{data: '{\"cmd\":\"set_light_switch\",\"value\":\"1\"}'}" --once
        """

        ok, msg = self.ros2_echo_and_pub(
            topic=topic,
            pub_cmd=cmd,
            expected_text="set_light_switch",
            echo_timeout=5
        )

        if not ok:
            return False, (
                "普通灯ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "普通灯ROS指令通信正常\n"
            "请人工确认灯光效果"
        )

    def test_red_blue_light(self) -> Tuple[bool, str]:

        topic = "/light_control"

        cmd = r"""
        ros2 topic pub /light_control std_msgs/msg/String "{data: '{\"cmd\":\"set_light_red_blue\",\"value\":\"1\"}'}" --times 2
        """

        ok, msg = self.ros2_echo_and_pub(
            topic=topic,
            pub_cmd=cmd,
            expected_text="set_light_red_blue",
            echo_timeout=5
        )

        if not ok:
            return False, (
                "红蓝灯ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "红蓝灯ROS指令通信正常\n"
            "亮度：20，请人工确认灯光效果"
        )

    def test_tts(self) -> Tuple[bool, str]:

        topic = "/tts_play"

        cmd = r"""
        ros2 topic pub /tts_play std_msgs/msg/String "{data: '{\"voice_name\":\"xiaoyan\",\"text\":\"测试\", \"play_count\": 1}'}" --once
        """

        ok, msg = self.ros2_echo_and_pub(
            topic=topic,
            pub_cmd=cmd,
            expected_text="测试",
            echo_timeout=5
        )

        if not ok:
            return False, (
                "TTS ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "TTS ROS指令通信正常\n"
            "请人工确认是否正常播放"
        )

    def get_timestamp(self):
        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def run_all_checks(self):

        timestamp_start = self.get_timestamp()

        print("\n")
        print("=" * 60)
        print("              机器狗测前检测")
        print("=" * 60)

        print(f"开始时间：{timestamp_start}")

        print("\n[1] SSH连接")
        print("⏳ 正在连接机器狗...")

        if not self.connect_ssh():
            print("❌ SSH连接失败，检测终止")
            return

        print("✅ SSH连接成功")

        print("\n[2] IMU检测")

        imu_ok, imu_msg = self.check_imu()

        print(
            f"【IMU】: "
            f"{'OK' if imu_ok else 'FAIL'}"
        )

        print(imu_msg)

        print("\n[3] RTK检测")

        rtk_ok, rtk_msg = self.check_rtk()

        print(
            f"【RTK】: "
            f"{'OK' if rtk_ok else 'FAIL'}"
        )

        print(rtk_msg)

        print("\n[4] 普通灯ROS检测")

        light_switch_ok, light_switch_msg = (
            self.test_light_switch()
        )

        print(
            f"【普通灯】: "
            f"{'OK' if light_switch_ok else 'FAIL'}"
        )

        print(light_switch_msg)

        print("\n[5] 红蓝灯ROS检测")

        red_blue_ok, red_blue_msg = (
            self.test_red_blue_light()
        )

        print(
            f"【红蓝灯】: "
            f"{'OK' if red_blue_ok else 'FAIL'}"
        )

        print(red_blue_msg)

        print("\n[6] TTS ROS检测")

        tts_ok, tts_msg = self.test_tts()

        print(
            f"【TTS】: "
            f"{'OK' if tts_ok else 'FAIL'}"
        )

        print(tts_msg)

        print("\n[7] 机器狗测前检测结果")

        print("\n" + "=" * 60)

        print("【传感器】")

        print(
            f"IMU          : "
            f"{'PASS' if imu_ok else 'FAIL'}"
        )

        print(
            f"RTK          : "
            f"{'PASS' if rtk_ok else 'FAIL'}"
        )

        print("\n【ROS2功能】")

        print(
            f"普通灯指令   : "
            f"{'PASS' if light_switch_ok else 'FAIL'}"
        )

        print(
            f"红蓝灯指令   : "
            f"{'PASS' if red_blue_ok else 'FAIL'}"
        )

        print(
            f"TTS指令      : "
            f"{'PASS' if tts_ok else 'FAIL'}"
        )

        all_ok = (
            imu_ok
            and rtk_ok
            and light_switch_ok
            and red_blue_ok
            and tts_ok
        )

        print("\n" + "=" * 60)

        if all_ok:
            print("✅ 机器狗测前检测完成：PASS")
        else:
            print("❌ 机器狗测前检测完成：FAIL")

        timestamp_end = self.get_timestamp()

        print(f"结束时间：{timestamp_end}")
        print("=" * 60)

        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    checker = DogChecker(
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=DOG_FRP_PORT,
        ssh_user=DOG_USER,
        ssh_password=DOG_PASSWORD,
        ssh_timeout=50,
        ssh_retry_interval=2
    )

    checker.run_all_checks()
