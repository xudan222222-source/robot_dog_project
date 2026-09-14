# Robot Dog Test Project

机器狗二次开发测试项目，主要用于机器狗、走线不同的背包及其下挂设备的通信、设备状态和基础功能测试。

---

## 1. 项目简介

本项目用于机器狗二次开发过程中的测试与问题定位，主要通过 Python 脚本对机器狗、背包及其下挂设备进行远程检查。

目前主要包含：

* 机器狗 IMU / RTK 状态检查
* 背包语音、麦克风等设备检查
* 四合一设备、网枪、摄像头等网络连通性检查
* FRP 服务及网络连接状态检查
* SSH 远程连接与设备状态检查

项目当前以 Python 脚本测试为主，后续可逐步扩展为基于 pytest 的自动化测试框架。

---

## 2. 项目结构

```text
robot_dog_project_github/
│
├── README.md
├── .gitignore
├── requirements.txt
├── config.py
│
├── frp_insp/
│   ├── FrpServiceMonitor01.py
│   ├── FrpServiceMonitor02.py
│   ├── frpLinkDownInsp.py
│   └── 解释.md
│
└── tests/
    ├── IMU_RTK_DogInsp.py
    ├── Speaker_Microphone_BackpackInsp_Old.py
    └── fourbox_gun_camera_BackpackInsp.py
```

### 目录说明

| 文件 / 目录            | 说明                |
| ------------------ | ----------------- |
| `README.md`        | 项目说明及使用方法         |
| `.gitignore`       | Git 忽略规则          |
| `.env`             | 本地敏感配置，不提交 GitHub |
| `requirements.txt` | Python 第三方依赖      |
| `config.py`        | 统一加载和管理配置         |
| `frp_insp/`        | FRP、网络及连接状态检查脚本   |
| `tests/`           | 机器狗及设备测试脚本        |

---

## 3. 环境要求

### 3.1 Windows 测试电脑

建议环境：

* Windows 10 / Windows 11
* Python 3.12+
* Git

### 3.2 Python 依赖

项目当前使用的主要第三方 Python 库：

* `paramiko`
* `python-dotenv`

具体版本以 `requirements.txt` 为准。

Python 标准库模块，例如：

```text
os
socket
subprocess
time
datetime
platform
shlex
typing
re
```

不需要单独安装，它们属于 Python 标准库。

---

## 4. 获取项目

使用 Git 克隆项目：

```bash
git clone <GitHub仓库地址>
```

进入项目目录：

```bash
cd robot_dog_project_github
```

---

## 5. 创建 Python 虚拟环境

建议使用虚拟环境运行项目，避免项目依赖与系统 Python 环境发生冲突。

在项目根目录执行：

```bash
python -m venv .venv
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
.venv\Scripts\activate.bat
```

激活成功后，终端前面通常会出现：

```text
(.venv)
```

---

## 6. 安装 Python 依赖

确保虚拟环境已经激活，然后执行：

```bash
pip install -r requirements.txt
```

安装完成后即可使用项目中的 Python 测试脚本。

---

## 7. 环境配置

项目使用 `.env` 文件保存设备连接信息及其他敏感配置。

### 7.1 创建 `.env`

```

然后根据实际设备环境编写 `.env`。

例如：

```env
# =========================
# 公司公网服务器
# =========================
PUBLIC_SERVER_IP=xxx.xxx.xxx.xxx

# =========================
# 机器狗
# =========================
DOG_USER=xxx
DOG_PASSWORD=xxx
DOG_ETHERNET_IP=192.168.xxx.xxx
DOG_FRP_PORT=xxx

# =========================
# 背包
# =========================
BACKPACK_USER=xxx
BACKPACK_PASSWORD=xxx
BACKPACK_FRP_PORT=xxx

# =========================
# 背包下挂设备
# =========================
FOUR_IN_ONE_IP=xxx.xxx.xxx.xxx
FOUR_IN_ONE_PORT=xxx
GUN_IP=xxx.xxx.xxx.xxx
CAMERA_IP=xxx.xxx.xxx.xxx
```


### 7.2 敏感信息说明

`.env` 中可能包含：

* 用户名
* 密码
* 公网服务器 IP
* 设备 IP
* FRP 端口
* 其他设备连接信息

因此：

**不要将 `.env` 提交到 GitHub。**

项目已经通过 `.gitignore` 对 `.env` 进行忽略。

---

## 8. 配置模块

项目通过 `config.py` 统一加载 `.env` 中的配置。

业务代码中通过：

```python
import config
```

使用配置。

例如：

```python
config.DOG_USER
config.DOG_PASSWORD
config.DOG_ETHERNET_IP
config.BACKPACK_FRP_PORT
```

这样可以避免在测试脚本中直接保存账号、密码和设备 IP，同时方便后续修改设备配置。

---

## 9. 机器狗环境

机器狗端运行：

```text
Ubuntu 22.04
ROS2 Humble
```

机器狗相关测试需要保证：

* 机器狗正常运行
* ROS2 Humble 环境正常
* 机器狗与背包网络连接正常
* FRP 服务正常
* SSH 可以正常连接机器狗或背包
* 对应 ROS2 Topic 正常发布

部分测试脚本会通过 SSH 远程连接机器狗或背包，并在远程设备上执行相关命令。

---

## 10. 网络连接关系

当前测试环境主要通过 FRP 实现远程设备访问。

基本网络关系：

```text
                  ┌────────────────────┐
                  │      测试电脑       │
                  │   Windows + Python │
                  └─────────┬──────────┘
                            │
                           FRP
                            │
                  ┌─────────▼──────────┐
                  │     公网服务器       │
                  │      FRP Server     │
                  └─────────┬──────────┘
                            │
                           FRP
                            │
                  ┌─────────▼──────────┐
                  │        背包          │
                  │   网络 / 设备管理    │
                  └─────────┬──────────┘
                            │
                         Ethernet
                            │
                  ┌─────────▼──────────┐
                  │       机器狗         │
                  │    Ubuntu 22.04     │
                  │     ROS2 Humble      │
                  └────────────────────┘
```

背包下还连接有其他设备，例如：

```text
背包
 ├── 四合一设备
 ├── 网枪
 └── 摄像头
```

具体 IP、端口及连接参数通过 `.env` 配置。

---

## 11. 测试脚本

### 11.1 机器狗 IMU / RTK 检查

```bash
python tests/IMU_RTK_DogInsp.py
```

主要检查：

* 机器狗 SSH 连接
* IMU 数据
* RTK 数据
* ROS2 Topic 状态

涉及的 ROS2 Topic 包括：

```text
/imu_data_ros   这个是非官网给的imu话题
/dog_imu_raw    是宇树b2官方发布的imu话题
/fix
```

---

### 11.2 背包语音 / 麦克风检查

```bash
python tests/Speaker_Microphone_BackpackInsp_Old.py
```

用于检查背包相关语音、麦克风等设备状态。

---

### 11.3 四合一 / 网枪 / 摄像头检查

```bash
python tests/fourbox_gun_camera_BackpackInsp.py
```

主要用于检查相关设备的网络连通性。

---

### 11.4 FRP 检查

`frp_insp/` 目录用于 FRP 服务、网络连接以及相关设备连接状态检查。

例如：

```bash
python frp_insp/FrpServiceMonitor.py
```

具体脚本功能以对应 Python 文件中的实现为准。

---

## 12. 常用检查方式

机器狗相关测试过程中，常用的 Linux / ROS2 命令包括：

```bash
ping
telnet
ssh
systemctl
journalctl
tail
ros2 topic list
ros2 topic echo
ros2 topic pub
```

例如检查 ROS2 Topic：

```bash
ros2 topic list
```

检查 IMU 数据：

```bash
timeout 5 ros2 topic echo /imu_data_ros | head -n 30
```

检查 RTK 数据：

```bash
timeout 5 ros2 topic echo /fix | head -n 50
```

---

## 13. 注意事项

1. 不要将 `.env` 提交到 GitHub。
2. 不要在 Python 代码中直接写入真实账号、密码及敏感 IP。
3. 运行机器狗相关测试前，确认网络和 FRP 连接正常。
4. 部分测试需要 SSH 登录权限。
5. ROS2 相关测试需要机器狗端 ROS2 环境正常。
6. 机器狗端使用的 ROS2 环境需要根据实际部署情况进行加载。
7. 不同设备的 IP、用户名、密码和 FRP 端口应根据实际环境修改 `.env`。

---

## 14. 后续计划

项目目前以 Python 测试脚本为基础，后续计划逐步完善：

* 统一测试代码结构
* 引入 pytest 自动化测试框架
* 增加测试用例管理
* 增加测试日志
* 增加测试报告
* 引入 Allure 测试报告
* 完善机器狗通信及设备自动化测试
* 提高问题定位和自动化执行能力

````