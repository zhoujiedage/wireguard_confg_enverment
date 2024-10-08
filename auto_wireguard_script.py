import subprocess
import os

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

def is_wireguard_installed():
    try:
        # 检查 WireGuard 是否已安装
        result = subprocess.run(['wg', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False
    
def install_wireguard():
    subprocess.run(['sudo', 'apt', 'update'])
    subprocess.run(['sudo', 'apt', 'install', 'wireguard'])

def generate_key_pair():
    subprocess.run("umask 077 && wg genkey | tee privatekey | wg pubkey > publickey", shell=True)
    with open('privatekey', 'r') as private_key_file:
        private_key = private_key_file.read().strip()
    with open('publickey', 'r') as public_key_file:
        public_key = public_key_file.read().strip()
    return private_key, public_key

def save_to_file(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)

def generate_server_config(server_private_key, listen_port, client_configs, server_ip):
    post_up_command = "iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE; ip6tables -A FORWARD -i wg0 -j ACCEPT; ip6tables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"
    post_down_command = "iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE; ip6tables -D FORWARD -i wg0 -j ACCEPT; ip6tables -t nat -D POSTROUTING -o eth0 -j MASQUERADE"
    peer_configs = "\n".join(client_configs)

    config_content = f"""
[Interface]
Address = 10.10.0.1/24
ListenPort = {listen_port}
PrivateKey = {server_private_key}
SaveConfig = false
PostUp = {post_up_command}
PostDown = {post_down_command}

{peer_configs}

"""
    save_to_file('/etc/wireguard/wg0.conf', config_content)
    print(f"Server Config File Content:\n{config_content}\n")

def generate_client_config(client_name, server_public_key, server_ip, listen_port, client_address_v4, client_address_v6):
    client_private_key, client_public_key = generate_key_pair()
    save_to_file(f'/etc/wireguard/{client_name}_private_key', client_private_key)
    save_to_file(f'/etc/wireguard/{client_name}_public_key', client_public_key)

    config_content = f"""
[Interface]
PrivateKey = {client_private_key}
Address = {client_address_v4}, {client_address_v6}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {server_ip}:{listen_port}
"""
    save_to_file(f'/etc/wireguard/{client_name}_wg.conf', config_content)
    print(f"{client_name} Config File Content:\n{config_content}\n")
    print(f"{client_name} Private Key: {client_private_key}")
    print(f"{client_name} Public Key: {client_public_key}\n")
    return client_public_key

def configure_ip_forwarding():
    try:
        # 打开 IPv4 转发
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'])
        # 打开 IPv6 转发
        subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.all.forwarding=1'])
        # 应用修改
        subprocess.run(['sudo', 'sysctl', '-p'])

        # 检查 sysctl.conf 是否已经包含相关配置
        with open('/etc/sysctl.conf', 'r') as sysctl_file:
            sysctl_lines = sysctl_file.readlines()

        ipv4_forward_line = 'net.ipv4.ip_forward=1\n'
        ipv6_forward_line = 'net.ipv6.conf.all.forwarding=1\n'

        if ipv4_forward_line not in sysctl_lines:
            with open('/etc/sysctl.conf', 'a') as sysctl_file:
                sysctl_file.write(ipv4_forward_line)

        if ipv6_forward_line not in sysctl_lines:
            with open('/etc/sysctl.conf', 'a') as sysctl_file:
                sysctl_file.write(ipv6_forward_line)

        print("IP forwarding enabled and set to start on boot.")
    except Exception as e:
        print(f"Error enabling IP forwarding: {e}")


def enable_wireguard_service():
    subprocess.run(['sudo', 'systemctl', 'enable', 'wg-quick@wg0'])
    subprocess.run(['sudo', 'systemctl', 'start', 'wg-quick@wg0'])
    subprocess.run(['sudo', 'systemctl', 'restart', 'wg-quick@wg0'])

def check_wireguard_status():
    subprocess.run(['sudo', 'systemctl', 'status', 'wg-quick@wg0'])

def cleanup_keys():
    # 删除密钥对文件，只保留配置文件
    key_files = ['privatekey', 'publickey','private_key','_public_key']
    for filename in os.listdir('/etc/wireguard'):
        for key_file in key_files:
            if key_file in filename:
                file_path = os.path.join('/etc/wireguard', filename)
                os.remove(file_path)
                print(f"Deleted file: {file_path}")

    # 修改 WireGuard 文件夹权限为 600
    subprocess.run(['sudo', 'chmod', '600', '/etc/wireguard'])

def main():
    if not is_wireguard_installed():
        install_wireguard()
    else:
        print("WireGuard is already installed.")
        
    server_private_key, server_public_key = generate_key_pair()
    save_to_file(f'/etc/wireguard/server_private_key', server_private_key)
    save_to_file(f'/etc/wireguard/server_public_key', server_public_key)
    server_ip = get_public_ip() or input("Enter server IP address (default is 43.153.101.210): ") or "43.153.101.210"
    listen_port = input("Enter WireGuard listen port (default is 51820): ") or "51820"
    num_clients = int(input("Enter the number of client configurations to generate (default is 2): ") or "2")

    client_configs = []
    for i in range(1, num_clients + 1):
        client_name = f'client{i}'
        client_address_v4 = f'10.10.0.{i + 1}/32'
        client_address_v6 = f'fd86:ea04:1111::{i + 1}/128'
        client_public_key = generate_client_config(client_name, server_public_key.replace('\n', ''), server_ip, listen_port, client_address_v4, client_address_v6)
        client_config = f"\n[Peer]\nPublicKey = {client_public_key}\nAllowedIPs = {client_address_v4}, {client_address_v6}\n"
        client_configs.append(client_config)

    generate_server_config(server_private_key, listen_port, client_configs, server_ip)
    configure_ip_forwarding()
    enable_wireguard_service()
    check_wireguard_status()
    cleanup_keys()  # 清理密钥对文件和修改权限

    print(f"Server IP address: {server_ip}")
    print(f"Server public key: {server_public_key}")
    print("Generated client key pairs, configuration files, and server configuration successfully.")

if __name__ == "__main__":
    main()
