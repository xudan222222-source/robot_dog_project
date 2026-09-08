import re
from datetime import datetime
import paramiko
import time
from typing import Tuple
from config import(
    PUBLIC_SERVER_IP,
    #背包
    BACKPACK_USER,BACKPACK_PASSWORD,BACKPACK_FRP_PORT
)

class BackPackChecker:
    def __init__(self, ssh_host: str, ssh_port: int, ssh_user: str, ssh_password: str,
                 ssh_timeout: int = 50, ssh_retry_interval: int = 2):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.ssh_timeout = ssh_timeout
        self.ssh_retry_interval = ssh_retry_interval
        self.conn = None

    # =======================
    # SSH 连接
    # =======================
    def connect_ssh(self) -> bool:
        start_time = time.time()
        while True:
            try:
                self.conn = paramiko.SSHClient()
                self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.conn.connect(hostname=self.ssh_host, port=self.ssh_port,
                                  username=self.ssh_user, password=self.ssh_password, timeout=10)
                return True
            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > self.ssh_timeout:
                    print(f"❌ SSH连接超时: {e}")
                    return False
                print(f"SSH连接失败，重试中... ({int(self.ssh_timeout - elapsed)}s剩余)")
                time.sleep(self.ssh_retry_interval)

    # =======================
    # 统一执行命令并注入 ROS 环境
    # =======================

    #如下 full_cmd 效果，等同=>狗/背包下直接运行:source /home/unitree/unitree_ros2/setup.sh
    # full_cmd = (
    #     "bash --login -c '"
    #     "source /opt/ros/foxy/setup.bash;"
    #     "source ~/unitree_ros2/cyclonedds_ws/install/setup.bash;"
    #     "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp;"
    #     "export CYCLONEDDS_URI=\"<CycloneDDS><Domain id=\\\"0\\\"><General><Interfaces>"
    #     "<NetworkInterface name=\\\"eth0\\\" priority=\\\"default\\\" multicast=\\\"default\\\"/>"
    #     "</Interfaces></General></Domain></CycloneDDS>\";"
    #     f"{cmd}"
    #     "'"
    # )

    def exec(self, cmd: str, timeout: int = 10) -> Tuple[str, str]:
        full_cmd = (
            "bash --login -c '"
            "source /home/unitree/unitree_ros2/setup.sh;"
            f"{cmd}"
            "'"
        )
        stdin, stdout, stderr = self.conn.exec_command(full_cmd, timeout=timeout + 2)
        out = stdout.read().decode(errors="ignore").strip()
        err = stderr.read().decode(errors="ignore").strip()
        return out, err

    # =======================
    # Speaker(扬声器)检查
    # =======================
    def check_Speaker_device(self) -> Tuple[bool, str]:
        cmd = 'aplay -l'
        out, err = self.exec(cmd)
        if out.strip():
            return True, f'Speaker已识别\n{out}'
        return False, out or err

    # =======================
    # Microphone（拾音器） 检查
    # =======================
    def check_Microphone_device(self) -> Tuple[bool, str]:
        cmd = 'arecord -l |grep USB'
        out, err = self.exec(cmd)
        if out.strip():
            return True, f'Microphone已识别\n{out}'
        return False, out or err

    # =======================
    # 获取当前时间戳
    # =======================
    def get_timestamp(self):
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run_all_checks(self):
        timestamp_start = self.get_timestamp()
        print(f"\n{timestamp_start}\n⏳ 正在连接背包...")
        if not self.connect_ssh():
            return
        print("✅ SSH 连接成功")

        speaker_ok, speaker_msg = self.check_Speaker_device()
        print(f"【扬声器】: {'OK' if speaker_ok else 'FAIL'} - {speaker_msg}")

        print("=============================================")

        microphone_ok, microphone_msg = self.check_Microphone_device()
        print(f"【拾音器】: {'OK' if microphone_ok else 'FAIL'} - {microphone_msg}")

        timestamp_end = self.get_timestamp()
        print(f"\n{timestamp_end} ✅ 扬声器、拾音器检查结束\n")


# =======================
# 主程序
# =======================
if __name__ == "__main__":
    checker = BackPackChecker(
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=BACKPACK_FRP_PORT,     #3588板卡
        ssh_user=BACKPACK_USER,
        ssh_password=BACKPACK_PASSWORD,
        ssh_timeout=50,
        ssh_retry_interval=2
    )
    checker.run_all_checks()