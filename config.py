import os
from dotenv import load_dotenv

load_dotenv()

PUBLIC_SERVER_IP = os.getenv("PUBLIC_SERVER_IP")

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