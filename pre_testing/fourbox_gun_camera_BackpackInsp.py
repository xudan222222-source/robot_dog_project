import shlex
from datetime import datetime
import paramiko
import time
from typing import Tuple
from config import(
    PUBLIC_SERVER_IP,
    #背包
    BACKPACK_FRP_PORT,BACKPACK_USER,BACKPACK_PASSWORD,
    #交换机下设备
    FOUR_IN_ONE_IP,FOUR_IN_ONE_PORT,GUN_IP,CAMERA_IP
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
        # =======================
        # SSH配置
        # =======================
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password

        self.ssh_timeout = ssh_timeout
        self.ssh_retry_interval = ssh_retry_interval

        self.conn = None

        # =======================
        # 设备IP及端口
        # =======================
        self.four_in_one_ip = four_in_one_ip
        self.four_in_one_port = four_in_one_port

        self.gun_ip = gun_ip
        self.camera_ip = camera_ip

    # =========================================================
    # SSH 连接
    # =========================================================
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

    # =========================================================
    # 统一执行命令并注入 ROS 环境
    # =========================================================
    def exec(self, cmd: str, timeout: int = 10) -> Tuple[str, str]:

        # ROS2 环境 + 实际执行命令
        shell_cmd = (
            "source /opt/ros/humble/setup.sh; "
            + cmd
        )

        # 使用 shlex.quote() 处理 bash -c 外层引号
        full_cmd = (
            f"bash --login -c {shlex.quote(shell_cmd)}"
        )

        stdin, stdout, stderr = self.conn.exec_command(
            full_cmd,
            timeout=timeout + 2
        )

        out = stdout.read().decode(errors="ignore").strip()
        err = stderr.read().decode(errors="ignore").strip()

        return out, err

    # =========================================================
    #ros2通信建立的echo逻辑
    # =========================================================
    def ros2_echo_and_pub(
            self,
            topic: str,
            pub_cmd: str,
            expected_text: str,
            echo_timeout: int = 5
    ) -> Tuple[bool, str]:
        """
        启动 ROS2 echo监听，
        发送一次 ROS2 指令，
        捕获 echo 输出结果。

        不使用远程log文件
        不使用PID管理
        不主动kill echo
        """

        # =====================================================
        # 1. 创建SSH channel，启动echo监听
        # =====================================================

        shell_cmd = (
            "source /opt/ros/humble/setup.sh; "
            f"timeout {echo_timeout} ros2 topic echo {topic}"
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

            # =====================================================
            # 2. 等待echo建立订阅
            # =====================================================

            time.sleep(1)

            # =====================================================
            # 3. 发布ROS指令
            # =====================================================

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

            # =====================================================
            # 4. 读取echo输出
            # =====================================================

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
                            f"echo内容:\n{echo_content}"
                        )

                # echo异常退出
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

            # =====================================================
            # 5. 关闭当前channel
            # =====================================================
            #
            # 不kill echo连接的 PID
            # 不影响其他SSH会话
            #
            if channel:
                channel.close()
    # =========================================================
    # Speaker（扬声器）检查
    # =========================================================
    def check_Speaker_device(self) -> Tuple[bool, str]:

        cmd = "aplay -l"

        out, err = self.exec(cmd)

        if out.strip():
            return True, f"Speaker已识别\n{out}"

        return False, out or err

    # =========================================================
    # Microphone（拾音器）检查
    # =========================================================
    def check_Microphone_device(self) -> Tuple[bool, str]:

        cmd = "arecord -l | grep USB"

        out, err = self.exec(cmd)

        if out.strip():
            return True, f"Microphone已识别\n{out}"

        return False, out or err

    # =========================================================
    # Ping设备
    # =========================================================
    def ping_device(
        self,
        device_name: str,
        ip: str
    ) -> Tuple[bool, str]:

        cmd = f"ping -c 3 -W 2 {ip}"

        out, err = self.exec(cmd)

        if "0% packet loss" in out:
            return True, f"{device_name}({ip}) 网络正常"

        return False, (
            f"{device_name}({ip}) 网络异常\n"
            f"{out or err}"
        )

    # =========================================================
    # Telnet端口检查
    # =========================================================
    def check_telnet_port(
        self,
        device_name: str,
        ip: str,
        port: int
    ) -> Tuple[bool, str]:

        # 使用 timeout 防止 telnet 一直阻塞
        cmd = (
            f"timeout 5 telnet {ip} {port} "
            "</dev/null 2>&1"
        )

        out, err = self.exec(cmd)

        result = f"{out}\n{err}".lower()

        # telnet连接成功通常会出现 connected / escape
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

    # =========================================================
    # ROS2：普通灯开关
    # =========================================================
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
                f"普通灯ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "普通灯ROS指令通信正常\n"
            "请人工确认灯光效果"
        )
    # =========================================================
    # ROS2：红蓝灯
    # =========================================================
    def test_red_blue_light(self) -> Tuple[bool, str]:

        topic = "/light_control"

        cmd = r"""
        ros2 topic pub /light_control std_msgs/msg/String "{data: '{\"cmd\":\"set_light_red_blue\",\"value\":\"1\"}'}" --once
        """

        ok, msg = self.ros2_echo_and_pub(
            topic=topic,
            pub_cmd=cmd,
            expected_text="set_light_red_blue",
            echo_timeout=5
        )

        if not ok:
            return False, (
                f"红蓝灯ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "红蓝灯ROS指令通信正常\n"
            "亮度：20，请人工确认灯光效果"
        )

    # =========================================================
    # ROS2：TTS
    # =========================================================
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
                f"TTS ROS检测失败\n"
                f"{msg}"
            )

        return True, (
            "TTS ROS指令通信正常\n"
            "请人工确认是否正常播放"
        )

    # =========================================================
    # 四合一完整检测
    # =========================================================
    def test_four_in_one(self):

        print("\n")
        print("=" * 60)
        print("                    四合一检测")
        print("=" * 60)

        # -----------------------------------------------------
        # 1. Ping
        # -----------------------------------------------------
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
                "跳过端口及功能测试"
            )

            return {
                "four_ping": False,
                "four_port": False,
                "light_switch": False,
                "red_blue_light": False,
                "tts": False
            }

        # -----------------------------------------------------
        # 2. Telnet
        # -----------------------------------------------------
        print("\n[2] 四合一端口检测")

        four_port_ok, four_port_msg = self.check_telnet_port(
            "四合一",
            self.four_in_one_ip,
            self.four_in_one_port
        )

        print(
            f"【四合一端口】: "
            f"{'OK' if four_port_ok else 'FAIL'}"
        )

        if not four_port_ok:
            print(four_port_msg)

            print(
                "⚠️ 四合一端口异常，"
                "跳过功能测试"
            )

            return {
                "four_ping": True,
                "four_port": False,
                "light_switch": False,
                "red_blue_light": False,
                "tts": False
            }

        # -----------------------------------------------------
        # 3. 四合一功能
        # -----------------------------------------------------
        print("\n[3] 四合一功能测试")

        print(
            "✅ 四合一网络及端口均正常，"
            "开始执行功能测试"
        )

        # 普通灯
        print("\n--- 普通灯 ---")

        light_switch_ok, light_switch_msg = (
            self.test_light_switch()
        )

        print(
            f"【普通灯】: "
            f"{'OK' if light_switch_ok else 'FAIL'}"
        )

        print(light_switch_msg)

        # 红蓝灯
        print("\n--- 红蓝灯 ---")

        red_blue_ok, red_blue_msg = (
            self.test_red_blue_light()
        )

        print(
            f"【红蓝灯】: "
            f"{'OK' if red_blue_ok else 'FAIL'}"
        )

        print(red_blue_msg)

        # TTS
        print("\n--- TTS ---")

        tts_ok, tts_msg = self.test_tts()

        print(
            f"【TTS】: "
            f"{'OK' if tts_ok else 'FAIL'}"
        )

        print(tts_msg)

        return {
            "four_ping": True,
            "four_port": True,
            "light_switch": light_switch_ok,
            "red_blue_light": red_blue_ok,
            "tts": tts_ok
        }

    # =========================================================
    # 获取当前时间戳
    # =========================================================
    @staticmethod
    def get_timestamp():

        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    # =========================================================
    # 主检测流程
    # =========================================================
    def run_all_checks(self):

        timestamp_start = self.get_timestamp()

        print("\n")
        print("=" * 60)
        print("              机器狗测前检测")
        print("=" * 60)
        print(f"开始时间：{timestamp_start}")

        # =====================================================
        # 1. SSH
        # =====================================================
        print("\n[1] SSH连接")

        print("⏳ 正在连接3588背包...")

        if not self.connect_ssh():

            print("❌ SSH连接失败，检测终止")
            return

        print("✅ SSH连接成功")

        # =====================================================
        # 2. 音频设备
        # =====================================================
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

        # =====================================================
        # 3. 摄像头开机提示
        # =====================================================
        print("\n" + "!" * 60)
        print("⚠️ 注意：请先将摄像头开机！")
        print("!" * 60)

        input(
            "确认摄像头已经开机后，"
            "按 Enter 继续四合一检测..."
        )

        # =====================================================
        # 4. 四合一完整检测
        # =====================================================
        print("\n[3] 四合一检测")

        four_result = self.test_four_in_one()

        # =====================================================
        # 5. 摄像头网络检测
        # =====================================================
        print("\n[4] 摄像头网络检测")

        camera_ok, camera_msg = self.ping_device(
            "摄像头",
            self.camera_ip
        )

        print(
            f"【摄像头】: "
            f"{'OK' if camera_ok else 'FAIL'}"
        )

        if not camera_ok:
            print(camera_msg)

        # =====================================================
        # 6. 网枪网络检测
        # =====================================================
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

        # =====================================================
        # 7. 最终结果
        # =====================================================
        print("\n[6] 测前检测结果")

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
        print(
            f"普通灯指令   : "
            f"{'PASS' if four_result['light_switch'] else 'FAIL'}"
        )
        print(
            f"红蓝灯指令   : "
            f"{'PASS' if four_result['red_blue_light'] else 'FAIL'}"
        )
        print(
            f"TTS指令      : "
            f"{'PASS' if four_result['tts'] else 'FAIL'}"
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

        # =====================================================
        # 总结果
        # =====================================================
        all_ok = (
            speaker_ok
            and microphone_ok
            and four_result["four_ping"]
            and four_result["four_port"]
            and four_result["light_switch"]
            and four_result["red_blue_light"]
            and four_result["tts"]
            and camera_ok
            and gun_ok
        )

        print("\n" + "=" * 60)

        if all_ok:
            print("✅ 机器狗测前检测完成：PASS")
        else:
            print("❌ 机器狗测前检测完成：FAIL")

        timestamp_end = self.get_timestamp()

        print(f"结束时间：{timestamp_end}")
        print("=" * 60)

        # =====================================================
        # 关闭SSH
        # =====================================================
        if self.conn:
            self.conn.close()


# =============================================================
# 主程序
# =============================================================
if __name__ == "__main__":

    checker = BackPackChecker(

        # ==========================
        # 3588 SSH
        # ==========================
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=BACKPACK_FRP_PORT,
        ssh_user=BACKPACK_USER,
        ssh_password=BACKPACK_PASSWORD,

        # ==========================
        # 交换机下设备
        # ==========================

        # 四合一
        four_in_one_ip=FOUR_IN_ONE_IP,
        four_in_one_port=FOUR_IN_ONE_PORT,

        # 网枪
        gun_ip=GUN_IP,

        # 大华-摄像头
        camera_ip=CAMERA_IP,

        ssh_timeout=50,
        ssh_retry_interval=2
    )

    checker.run_all_checks()