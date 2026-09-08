import socket
import paramiko
import time
from datetime import datetime
import subprocess
import platform

from config import (
    PUBLIC_SERVER_IP,
    #狗端
    DOG_USER,DOG_PASSWORD,DOG_ETHERNET_IP,DOG_FRP_PORT,
    #背包端
    BACKPACK_USER,BACKPACK_PASSWORD,BACKPACK_ETHERNET_IP,BACKPACK_FRP_PORT
)

#检测间隔
CHECK_INTERVAL = 2

# ========== 工具函数 ==========
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ping_once(host="baidu.com", count=1, timeout=2):
    param = "-n" if platform.system() == "Windows" else "-c"
    cmd = ["ping", param, str(count), "-W", str(timeout), host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def ssh_exec(host, port, user, password, command, timeout=5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port, user, password, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=10)
        output = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        client.close()
        return True, output + ("\n" + err if err else "")
    except Exception as e:
        return False, str(e)


def frp_tunnel_ok(host, port):
    try:
        socket.create_connection((host, port), timeout=3)
        return True
    except:
        return False


# ========== 主监控 ==========
def monitor():
    print(f"{get_timestamp()} - 🐕 监控启动（狗端口={DOG_FRP_PORT}）")

    while True:
        ts = get_timestamp()

        # ---- 1. 尝试frp连狗 ----
        dog_ok = frp_tunnel_ok(PUBLIC_SERVER_IP, DOG_FRP_PORT)
        dog_ssh_ok = False
        #输入command,系统输出内容
        dog_ssh = ""

        if dog_ok:
            dog_ssh_ok, dog_ssh = ssh_exec(PUBLIC_SERVER_IP, DOG_FRP_PORT, DOG_USER, DOG_PASSWORD,
                                           "systemctl is-active insp_doggo")

        # ---- 2. 尝试frp连背包 ----
        bp_ok, _ = ssh_exec(PUBLIC_SERVER_IP, BACKPACK_FRP_PORT, BACKPACK_USER, BACKPACK_PASSWORD,
                            "echo ok")

        # ---- 3. 都连不上 → 无网络 ----
        if not dog_ok and not bp_ok:
            print(f"{ts} - ❌ ssh直连不上，无网络")
            time.sleep(CHECK_INTERVAL)
            continue

        # ---- 4. 狗frp连接失败，但背包能连 → 背包中转 ----
        if not dog_ok and bp_ok:
            print(f"{ts} - ⚠️ 狗frp失败，切背包中转...")

            # 1. 先通过背包直连狗的网口IP（宇树机器提供的IP，需替换成实际值）
            ok, out = ssh_exec(DOG_ETHERNET_IP, 22, DOG_USER, DOG_PASSWORD, "hostname")

            if not ok:
                print(f"{ts} - ❌ 背包→狗 SSH 失败，可能是连接线问题")
            else:
                print(f"{ts} - ✅ 背包可通过网口直连狗（{out.strip()}）")

                # 2. 狗端frp失败，通过网口直连狗端，ssh到狗端系统，查看是否ping通baidu
                ok, out = ssh_exec(DOG_ETHERNET_IP, 22, DOG_USER, DOG_PASSWORD, "ping -c 1 baidu.com")
                if ok and "1 received" in out:
                    print(f"{ts} - ✅ 狗端有网络")

                    # 3. 追溯 frp 服务状态
                    ok, out = ssh_exec(DOG_ETHERNET_IP, 22, DOG_USER, DOG_PASSWORD,
                                       "systemctl is-active frpc.service")
                    if ok and "active" in out:
                        print(f"{ts} - ✅ 通过网口连接狗端，显示狗端frpc.service active")
                    else:
                        print(f"{ts} - 🔴 frp.service fail，日志如下：")
                        ok2, log = ssh_exec(DOG_ETHERNET_IP, 22, DOG_USER, DOG_PASSWORD,
                                            "journalctl -u frpc.service -n 50 --no-pager")
                        if ok2:
                            for line in log.splitlines():
                                print(f"    {line}")
                        else:
                            print(f"{ts} - ⚠️ 拉日志失败: {log}")
                else:
                    print(f"{ts} - ❌ 狗端无网络（ping baidu.com 失败）")


        # ---- 5. 狗frp连接成功 → 正常检测 ----
        elif dog_ok:
            if dog_ssh_ok:
                if "active" in dog_ssh:
                    print(f"{ts} - ✅ 狗端insp_doggo服务 active")
                else:
                    print(f"{ts} - ❌ 狗端insp_doggo服务 inactive")
            else:
                print(f"{ts} - ⚠️狗端使用frp远程连接失败: {dog_ssh}")


        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor()
