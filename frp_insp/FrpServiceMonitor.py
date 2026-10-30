import paramiko
from datetime import datetime
from config import PUBLIC_SERVER_IP, DOG_FRP_PORT, DOG_USER, DOG_PASSWORD

def ssh_dog_connect() -> bool:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=PUBLIC_SERVER_IP,
            port=DOG_FRP_PORT,
            username=DOG_USER,
            password=DOG_PASSWORD,
            timeout=5
        )
        client.close()
        return True
    except Exception:
        return False

def get_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    t = get_ts()
    if ssh_dog_connect():
        print(f"{t} - ✅ 狗端SSH连接正常")
    else:
        print(f"{t} - ❌ SSH狗端连不上，请尝试使用背包ping狗端")
