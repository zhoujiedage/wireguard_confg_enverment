import subprocess

def get_public_ip():
    try:
        # 使用 curl 命令获取公共 IP
        result = subprocess.run(['curl', 'ifconfig.me'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None

# 测试获取公共 IP 的函数
public_ip = get_public_ip()
print(public_ip)
