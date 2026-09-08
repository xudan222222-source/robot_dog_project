#!/usr/bin/env python3
import subprocess, time
from datetime import datetime
from config import DOG_ETHERNET_IP

def ts():
    return datetime.now().strftime("%H:%M:%S")

def run(cmd, timeout=10):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.returncode

def check_frpc():
    out, _ = run("systemctl is-active frpc")
    return out == "active"

def check_nic():
    out, _ = run("ip link show eth0")
    return "state UP" in out

def check_gw():
    out, rc = run(f"ping -c 5 -W 2 {DOG_ETHERNET_IP}")
    return rc == 0 and "100% loss" not in out

def check_ext():
    out, rc = run("ping -c 5 -W 2 8.8.8.8")
    return rc == 0 and "100% loss" not in out

def diagnose(label):
    print(f"\n[{ts()}] {label}")

    if not check_frpc():
        print(f"[{ts()}] ❌ frpc 没跑")
        return "FRPC_NOT_RUNNING"
    print(f"[{ts()}] ✅ frpc 运行中")

    if not check_nic():
        print(f"[{ts()}] ❌ 网卡 Down")
        return "NIC_DOWN"
    print(f"[{ts()}] ✅ 网卡正常")

    if not check_gw():
        print(f"[{ts()}] ❌ 网关不通")
        return "GATEWAY_DOWN"
    print(f"[{ts()}] ✅ 网关正常")

    if not check_ext():
        print(f"[{ts()}] ❌ 外网不通")
        return "EXTERNAL_DOWN"
    print(f"[{ts()}] ✅ 外网正常")

    print(f"[{ts()}] ⚠️ 全部正常 → frps 那边的问题")
    return "FRPS_DOWN"

# 开机先跑一次
print(f"[{ts()}] 开机自检")
result = diagnose("【开机】")
if result != "FRPS_DOWN":
    print(f"[{ts()}] 开机就有问题: {result}")
    exit(0)

# 持续监控
print(f"[{ts()}] 进入监控，每5秒检查一次")
while True:
    time.sleep(5)
    if not check_frpc():
        result = diagnose("【断连】")
        print(f"[{ts()}] 断连原因: {result}")
