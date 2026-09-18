def check_enabled_services(self):
    """
    检查 /etc/systemd/system/ 下的 enabled 服务。{软件程序的，非整个狗本体的}

    enabled + active  -> PASS
    enabled + 非active -> FAIL + 状态 + 日志
    """

    # 获取 /etc/systemd/system/ 下的 service 文件
    result = self.exec(
        "find /etc/systemd/system/ -maxdepth 1 -name '*.service' -type f"
    )

    if not result:
        print("未找到 systemd service 文件")
        return False

    services = result.strip().splitlines()
    all_pass = True

    for service_path in services:
        service_name = service_path.split("/")[-1]

        # 1. 判断是否开机自启
        enabled = self.exec(
            f"systemctl is-enabled {service_name} 2>/dev/null"
        ).strip()

        if enabled != "enabled":
            continue

        # 2. 获取当前状态
        active = self.exec(
            f"systemctl is-active {service_name} 2>/dev/null"
        ).strip()

        # 3. 正常
        if active == "active":
            print(f"[PASS] {service_name} : enabled + active")
            continue

        # 4. 异常
        all_pass = False

        print(f"[FAIL] {service_name}")
        print(f"       自启动：{enabled}")
        print(f"       当前状态：{active}")

        # 5. 打印最近日志
        logs = self.exec(
            f"journalctl -u {service_name} -n 20 --no-pager 2>/dev/null"
        )

        print("       日志：")
        if logs.strip():
            for line in logs.strip().splitlines():
                print(f"       {line}")
        else:
            print("       无相关日志")

    return all_pass