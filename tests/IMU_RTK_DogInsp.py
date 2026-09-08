import re
from datetime import datetime
import paramiko
import time
from typing import Tuple
from config import(
    PUBLIC_SERVER_IP,
    #狗端
    DOG_USER,DOG_PASSWORD,DOG_FRP_PORT
)

class DogChecker:
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


#b2的17024hy背包已不含继电器

    # =======================
    # 继电器检查
    # =======================

    # def check_light_control_device(self) -> Tuple[bool, str]:
    #     cmd = 'if [ -e "/dev/light_control" ]; then echo "继电器已识别"; else echo "继电器未识别"; exit 1; fi'
    #     out, err = self.exec(cmd)
    #     if "继电器已识别" in out:
    #         return True, '继电器已识别'
    #     return False, out or err


    # =======================
    # IMU 检查
    # =======================
    def check_imu(self) -> Tuple[bool, str]:
        """
        修复：SSH 环境下 ros2 topic list 为空的问题（已正确加载环境）
        """
        #/imu_data_ros是 小灰狗 额外买的 imu 的话题；/dog_imu_raw是b2的imu话题
        cmd = r"""
        timeout 5 ros2 topic echo /dog_imu_raw | head -n 50
        """
        out, err = self.exec(cmd)
        if "orientation:" in out and "angular_velocity:" in out and "linear_acceleration:" in out:
            return True, "IMU 检查: 成功 - 数据存在"
        else:
            return False, f"IMU 检查: 失败 - 数据缺失\n{out}\n{err}"

    # =======================
    # RTK 检查（只要有数据就算 OK）
    # =======================
    def check_rtk(self) -> Tuple[bool, str]:
        """
        RTK 检查（只要有数据就算 OK）
        status 仅用于展示
        """
        cmd = r"""
            timeout 5 ros2 topic echo /fix | head -n 50
        """
        out, err = self.exec(cmd)

        # --- ① 数据完全为空 → FAIL ---
        if not out.strip():
            return False, "RTK 检查: 失败 - 无数据"

        # --- ② 提取第一个 status 值 ---
        match = re.search(r"status:\s*\n\s*status:\s*(-?\d+)", out)

        if match:
            status_value = int(match.group(1))
        else:
            status_value = None

        # --- ③ 根据 status 映射说明文本 ---
        status_map = {
            2: "固定解 (精确导航)",
            1: "浮点解 (粗略可用)",
            0: "单点定位 (米级精度)",
            -1: "无定位",
        }

        if status_value in status_map:
            status_text = status_map[status_value]
        else:
            status_text = f"未知状态 ({status_value})"

        # --- ④ 返回最终结果（RTK 总是 OK 只要有数据） ---
        return True, f"RTK 检查: 成功 - {status_text}"

    # =======================
    # 获取当前时间戳
    # =======================
    def get_timestamp(self):
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =======================
    # 汇总
    # =======================
    def run_all_checks(self):
        timestamp_start = self.get_timestamp()
        print(f"\n{timestamp_start}\n⏳ 正在连接机器狗...")
        if not self.connect_ssh():
            return
        print("✅ SSH 连接成功")

        # light_ok, light_msg = self.check_light_control_device()
        # print(f"【继电器】: {'OK' if light_ok else 'FAIL'} - {light_msg}")

        imu_ok, imu_msg = self.check_imu()
        print(f"【IMU】: {'OK' if imu_ok else 'FAIL'} - {imu_msg}")

        rtk_ok, rtk_msg = self.check_rtk()
        print(f"【RTK】: {'OK' if rtk_ok else 'FAIL'} - {rtk_msg}")

        timestamp_end = self.get_timestamp()
        print(f"\n{timestamp_end} ✅IMU、RTK检查结束\n")


# =======================
# 主程序
# =======================
if __name__ == "__main__":
    checker = DogChecker(
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=DOG_FRP_PORT,     #Dog的Frp
        ssh_user=DOG_USER,
        ssh_password=DOG_PASSWORD,
        ssh_timeout=50,
        ssh_retry_interval=2
    )
    checker.run_all_checks()
