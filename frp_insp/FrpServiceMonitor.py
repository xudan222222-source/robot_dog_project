import socket
import paramiko
import time
from datetime import datetime
from config import PUBLIC_SERVER_IP,BACKPACK_FRP_PORT,BACKPACK_USER,BACKPACK_PASSWORD


# 检测间隔（秒）
CHECK_INTERVAL = 10


def check_frp_with_retry(max_retries=3, delay=1):
    """检测 FRP 隧道是否可用（带重试）"""
    for attempt in range(max_retries):
        try:
            with socket.create_connection((PUBLIC_SERVER_IP, BACKPACK_FRP_PORT), timeout=3):
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(delay)
    return False


def check_service_via_ssh():
    """通过 SSH 检测服务状态"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(PUBLIC_SERVER_IP, BACKPACK_FRP_PORT, BACKPACK_USER, BACKPACK_PASSWORD, timeout=5)


        stdin, stdout, _ = client.exec_command("systemctl is-active insp_doggo")
        status = stdout.read().decode().strip()
        client.close()


        return status == "active"
    except:
        return False


def get_timestamp():
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def monitor():
    """主监控循环"""
    while True:
        timestamp = get_timestamp()
        try:
            # 检测 FRP 隧道
            if check_frp_with_retry():
                # FRP 可用时检测服务
                # print('Frp已连接')
                if check_service_via_ssh():
                    print(f"{timestamp} - ✅ 服务active")
                else:
                    print(f"{timestamp} - ❌ 服务inactive")
            else:
                print(f"{timestamp} - ⚠️ 狗连接不上")

        except Exception as e:
            print(f"{timestamp} - ❌ 监控异常: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    print("FRP 服务监控启动...")
    monitor()
