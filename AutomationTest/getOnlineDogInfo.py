from playwright.sync_api import sync_playwright
from config import BACKEND_URL,USER_NAME,UER_PASSWORD
import json
import sys

LOGIN_PAGE_URL = f"{BACKEND_URL}/login"
TARGET_API_URL = "/api/real_time_model/get_robotic_info"

# 登录元素定位，根据你页面改成实际xpath/selector
USER_LOC = 'input[placeholder="账号"]'
PWD_LOC = 'input[placeholder="密码"]'
CAPTCHA_LOC = 'input[placeholder="验证码"]'
SUBMIT_BTN_LOC = 'button:has-text("登录")'
# 新增：获取控制权按钮
GET_CONTROL_BTN_LOC = "div.controlBtn >> div:has-text('获取控制权')"
#新增：释放控制权
RELEASE_CONTROL_BIN_LOC = "div.controlBtn >> div:has-text('已获取')"
#确认释放控制权
CONFIRM = "button.release-confirm-btn"

robot_list = []

def handle_response(resp):
    if TARGET_API_URL in resp.url and resp.status == 200:
        try:
            res_json = resp.json()
            if res_json.get("success") and res_json.get("data"):
                for item in res_json["data"]:
                    if item.get("roboticDogStatus") is True and item.get("controlPower") is False:
                        robot_info = {
                            "sn": item["roboticSn"],
                            "name": item["roboticDogName"],
                            "model": item["roboticModel"]
                        }
                        robot_list.append(robot_info)
                        print(f"抓到符合条件机器狗：SN={robot_info['sn']}, name={robot_info['name']}")
        except Exception as e:
            print(f"解析响应失败：{e}")

def get_target_robot(key: str):
    """
    入参兼容：机器名称 / SN编号
    优先级：先匹配name，name找不到再匹配sn
    ⚠️ 只有传入参数的时候才会调用这个函数，不传参不会走到这里
    """
    # 第一步：先按name查找
    for robot in robot_list:
        if robot["name"] == key:
            return robot
    # 第二步：name没找到，再按sn查找
    for robot in robot_list:
        if robot["sn"] == key:
            return robot
    # 传了参数但是全都找不到，抛出异常
    raise Exception(f" 机器狗列表未找到对应可操作的机器狗！")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.on("response", handle_response)

        # 打开登录页
        page.goto(LOGIN_PAGE_URL)
        page.wait_for_load_state("domcontentloaded")

        # 填账号密码
        page.locator(USER_LOC).fill(USER_NAME)
        page.locator(PWD_LOC).fill(UER_PASSWORD)
        print("\n===== 请在浏览器窗口手动输入验证码，输入完成后，在调试面板点【继续】 =====")
        page.pause()

        # 点击登录
        page.locator(SUBMIT_BTN_LOC).click()
        page.wait_for_url("**/realtimeControlNew/index", timeout=5000)
        page.wait_for_load_state("networkidle")

        # 等待列表接口请求返回
        page.wait_for_timeout(4000)

        print(f"\n===== 一共抓到 {len(robot_list)} 台可控制机器狗 =====")
        if not robot_list:
            raise Exception("没有抓到【在线+可控制】的机器狗！")

        # ========= 抓完数据之后，才读取命令行参数 =========
        if len(sys.argv) >= 2:
            input_key = sys.argv[1]
            target_robot = get_target_robot(input_key)
            print(f"\n===== 匹配成功，选中目标机器狗 =====")
            print(target_robot)

            # 用SN定位复选框
            # ✅ 点击可视化方框，不再操作隐藏原生input
            checkbox_loc = page.locator(
                f'label:has(input.el-checkbox__original[value="{target_robot["sn"]}"]) >> .el-checkbox__inner')
            checkbox_loc.wait_for(state="visible", timeout=3000)
            checkbox_loc.click()
            print(f" 已点击可视化勾选框 SN={target_robot['sn']}")

            page.wait_for_timeout(2000)

            # ===================== 新增：获取控制权 =====================
            control_btn = page.locator(GET_CONTROL_BTN_LOC)
            control_btn.wait_for(state="visible", timeout=3000)
            control_btn.click()
            print("已点击【获取控制权】按钮")
            # 你可以在这里加等待，等后端返回控制权结果
            page.wait_for_timeout(3000)
            # =========================================================

        else:
            # 👉 没有传参：仅展示列表，不获取控制权、不勾选、不抛异常
            print("\n未传入机器狗名称/SN，仅展示当前可控制列表，暂不获取控制权：")
            for idx, r in enumerate(robot_list):
                print(f"[{idx+1}] name: {r['name']}, sn: {r['sn']}, model: {r['model']}")

        browser.close()

if __name__ == "__main__":
    run()
