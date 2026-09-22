import time
from typing import Tuple

import paramiko


class BackPackServiceChecker:

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_password: str,
        ssh_timeout: int = 50,
        ssh_retry_interval: int = 2
    ):
        """
        初始化背包检测对象
        """

        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password

        self.ssh_timeout = ssh_timeout
        self.ssh_retry_interval = ssh_retry_interval

        self.conn = None

    def connect_ssh(self) -> bool:
        """
        建立 SSH 连接
        """

        start_time = time.time()

        while True:
            try:
                self.conn = paramiko.SSHClient()

                # 自动接受远程主机的 SSH Key
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

                print(
                    f"[PASS] SSH 连接成功："
                    f"{self.ssh_host}:{self.ssh_port}"
                )

                return True

            except Exception as e:
                elapsed = time.time() - start_time

                if elapsed > self.ssh_timeout:
                    print(f"[FAIL] SSH 连接超时：{e}")
                    return False

                remaining_time = int(
                    self.ssh_timeout - elapsed
                )

                print(
                    f"[WARN] SSH 连接失败，重试中..."
                    f"（{remaining_time}s 剩余）"
                )

                time.sleep(self.ssh_retry_interval)

    def exec(
        self,
        cmd: str,
        timeout: int = 10
    ) -> Tuple[str, str]:
        """
        执行远程 Linux 命令

        返回：
            stdout：标准输出
            stderr：标准错误
        """

        if self.conn is None:
            raise RuntimeError(
                "SSH 尚未连接，请先调用 connect_ssh()"
            )

        full_cmd = (
            "bash --login -c '"
            f"{cmd}"
            "'"
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

    def check_services(self) -> bool:
        """
        检查 /etc/systemd/system/ 下的 service 文件。

        检查规则：

        1. 非 enabled 服务直接跳过
        2. enabled + active 视为通过
        3. enabled + 非 active 视为失败
        4. 失败时打印具体状态和最近 20 条日志
        """

        print("\n========== Systemd 服务检测 ==========")

        # 获取远程机器上的 service 文件
        find_service_cmd = (
            "find /etc/systemd/system/ "
            "-maxdepth 1 "
            "-type f "
            "-name '*.service'"
        )

        out, err = self.exec(find_service_cmd)

        if err:
            print(
                f"[FAIL] 获取 systemd 服务文件失败：{err}"
            )
            return False

        service_paths = out.splitlines()

        if not service_paths:
            print(
                "[WARN] /etc/systemd/system/ "
                "下未找到 service 文件"
            )
            return True

        all_pass = True
        enabled_count = 0

        for service_path in service_paths:

            # 从完整路径中提取服务名
            service_name = service_path.rsplit(
                "/",
                1
            )[-1]

            # 判断服务是否设置为开机自启动
            enabled_out, _ = self.exec(
                f"systemctl is-enabled "
                f"{service_name} 2>/dev/null"
            )

            enabled_status = enabled_out.strip()

            # 不是 enabled 的服务跳过
            if enabled_status != "enabled":
                continue

            enabled_count += 1

            # 判断当前运行状态
            active_out, _ = self.exec(
                f"systemctl is-active "
                f"{service_name} 2>/dev/null"
            )

            active_status = active_out.strip()

            # enabled + active
            if active_status == "active":
                print(
                    f"[PASS] {service_name} "
                    f": enabled + active"
                )
                continue

            # enabled 但是当前未正常运行
            all_pass = False

            print(f"\n[FAIL] {service_name}")
            print(
                f"       自启动状态：{enabled_status}"
            )
            print(
                f"       当前运行状态：{active_status}"
            )

            # 获取最近 20 条服务日志
            log_out, log_err = self.exec(
                f"journalctl -u {service_name} "
                f"-n 20 "
                f"--no-pager "
                f"2>/dev/null"
            )

            print("       最近日志：")

            if log_out:
                for line in log_out.splitlines():
                    print(f"       {line}")
            else:
                print("       无相关日志")

        print("\n========== Systemd 检测结果 ==========")

        if enabled_count == 0:
            print("[WARN] 未找到 enabled 服务")
            return True

        if all_pass:
            print(
                f"[PASS] 共有 {enabled_count} 个 enabled 服务，"
                f"全部 active"
            )
        else:
            print(
                f"[FAIL] 共有 {enabled_count} 个 enabled 服务，"
                f"存在异常服务"
            )

        return all_pass

    def close_ssh(self):
        """
        关闭 SSH 连接
        """

        if self.conn is not None:
            self.conn.close()
            self.conn = None

            print("[INFO] SSH 连接已关闭")


if __name__ == "__main__":

    from config import (
        PUBLIC_SERVER_IP,
        BACKPACK_FRP_PORT,
        BACKPACK_USER,
        BACKPACK_PASSWORD
    )

    backpackService_checker = BackPackServiceChecker(
        ssh_host=PUBLIC_SERVER_IP,
        ssh_port=BACKPACK_FRP_PORT,
        ssh_user=BACKPACK_USER,
        ssh_password=BACKPACK_PASSWORD
    )

    try:
        if backpackService_checker.connect_ssh():
            backpackService_checker.check_services()

    finally:
        backpackService_checker.close_ssh()