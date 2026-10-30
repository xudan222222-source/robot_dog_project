import os
from dotenv import load_dotenv

load_dotenv()
#网络、服务 检测参数
PUBLIC_SERVER_IP = os.getenv("PUBLIC_SERVER_IP")

ROBOT_SN = os.getenv("ROBOT_SN")
DOG_USER = os.getenv("DOG_USER")
DOG_PASSWORD = os.getenv("DOG_PASSWORD")
DOG_ETHERNET_IP = os.getenv("DOG_ETHERNET_IP")
DOG_FRP_PORT = os.getenv("DOG_FRP_PORT")

BACKPACK_USER = os.getenv("BACKPACK_USER")
BACKPACK_PASSWORD = os.getenv("BACKPACK_PASSWORD")
BACKPACK_ETHERNET_IP = os.getenv("BACKPACK_ETHERNET_IP")
BACKPACK_FRP_PORT = os.getenv("BACKPACK_FRP_PORT")

FOUR_IN_ONE_IP = os.getenv("FOUR_IN_ONE_IP")
FOUR_IN_ONE_PORT = os.getenv("FOUR_IN_ONE_PORT")
GUN_IP = os.getenv("GUN_IP")
CAMERA_IP = os.getenv("CAMERA_IP_daHua")

#接口 参数
BACKEND_URL = os.getenv("BACKEND_URL")
BACKEND_URL2 = os.getenv("BACKEND_URL2")
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN")
#前端页面渲染
UER_ID = os.getenv("UER_ID")
USER_NAME = os.getenv("USER_NAME")
UER_PASSWORD = os.getenv("UER_PASSWORD")
#接口提取token
APPID = os.getenv("APPID")
