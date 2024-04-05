import time
import subprocess
import socket
import os

def get_public_ip():
    try:
        # 创建套接字连接到外部IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print("Error:", e)
        return None

def install_wireguard():
    subprocess.run(['sudo', 'apk', 'update'])
    subprocess.run(['sudo', 'apk', 'add', 'wireguard-tools'])

def generate_key_pair():
    # 生成私钥
    private_key_process = subprocess.run(['wg', 'genkey'], capture_output=True, text=True)
    private_key = private_key_process.stdout.strip()

    # 生成公钥
    public_key_process = subprocess.run(['echo', '-n', private_key], stdout=subprocess.PIPE, text=True)
    public_key_process = subprocess.run(['wg', 'pubkey'], input=public_key_process.stdout, capture_output=True, text=True)
    public_key = public_key_process.stdout.strip()

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
        os.system('sysctl -w net.ipv4.ip_forward=1')
        # 打开 IPv6 转发
        os.system('sysctl -w net.ipv6.conf.all.forwarding=1')
        # 将修改写入 sysctl.conf，确保在系统重启时生效
        with open('/etc/sysctl.conf', 'a') as sysctl_file:
            sysctl_file.write('\nnet.ipv4.ip_forward=1\nnet.ipv6.conf.all.forwarding=1\n')

        print("IP forwarding enabled and set to start on boot.")
    except Exception as e:
        print(f"Error enabling IP forwarding: {e}")

def enable_wireguard_service():
    try:
        subprocess.run(['sudo', 'rc-update', 'add', 'wg-quick@wg0', 'default'], check=True)
        subprocess.run(['sudo', 'rc-service', 'wg-quick@wg0', 'start'], check=True)
        time.sleep(1)  # 添加适当的延迟
        subprocess.run(['sudo', 'rc-service', 'wg-quick@wg0', 'status'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def check_wireguard_status():
    try:
        subprocess.run(['sudo', 'rc-service', 'wg-quick@wg0', 'status'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

# 调用示例


def main():
    install_wireguard()
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

    print(f"Server IP address: {server_ip}")
    print(f"Server public key: {server_public_key}")
    print("Generated client key pairs, configuration files, and server configuration successfully.")

if __name__ == "__main__":
    main()
