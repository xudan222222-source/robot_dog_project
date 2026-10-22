from lighting_test.LightControlTester import LightControlTester
from data_communication_test.authorization import get_authorization_token
import paramiko
import time
from config import (
    PUBLIC_SERVER_IP,
    DOG_FRP_PORT,
    DOG_USER,
    DOG_PASSWORD,
    BACKPACK_FRP_PORT,
    BACKPACK_USER,
    BACKPACK_PASSWORD
)


def ssh_run_once(host, port, user, password, cmd):
    """一次性执行短命令（ls检测behavior目录），返回输出字符串"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=user, password=password, timeout=10)
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return out, err
    finally:
        client.close()


def detect_behavior_location() -> tuple[str, dict]:
    """判断behavior业务跑在狗本体还是背包"""
    out, err = ssh_run_once(
        host=PUBLIC_SERVER_IP,
        port=DOG_FRP_PORT,
        user=DOG_USER,
        password=DOG_PASSWORD,
        cmd="cd ~/ywsz/ota/behavior && ls"
    )
    print(f"\n>>> 检测behavior目录输出：\n{out}, err:{err}")
    if out.strip() != "pass":
        print(">>> behavior 在【狗本体】")
        return "dog", {
            "host": PUBLIC_SERVER_IP,
            "port": DOG_FRP_PORT,
            "user": DOG_USER,
            "password": DOG_PASSWORD
        }
    else:
        print(">>> behavior 在【背包RK3588】")
        return "bag", {
            "host": PUBLIC_SERVER_IP,
            "port": BACKPACK_FRP_PORT,
            "user": BACKPACK_USER,
            "password": BACKPACK_PASSWORD
        }


class BehaviorSshStream:
    """独立的ssh流式对象，专门给light_tester读取tail日志用"""
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client = None

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            timeout=10
        )

    def stream_command(self, cmd, get_pty=True):
        stdin, stdout, stderr = self.client.exec_command(cmd, get_pty=get_pty)
        return stdin, stdout, stderr

    def close(self):
        if self.client:
            self.client.close()


if __name__ == "__main__":
    tester = LightControlTester()
    behavior_tag, behavior_cfg = detect_behavior_location()

    # 新建独立ssh连接，专门用来tail日志
    behavior_ssh = BehaviorSshStream(
        host=behavior_cfg["host"],
        port=behavior_cfg["port"],
        user=behavior_cfg["user"],
        password=behavior_cfg["password"]
    )
    behavior_ssh.connect()

    token = get_authorization_token()
    tester.run_all_cases(behavior_ssh=behavior_ssh, token=token)

    behavior_ssh.close()
