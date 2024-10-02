import re

def clean_ip_forwarding(file_path):
    try:
        # 读取原文件内容
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # 正则表达式匹配要删除的行
        pattern = re.compile(r'^(net\.ipv4\.ip_forward=1|net\.ipv6\.conf\.all\.forwarding=1)$')
        
        # 创建一个新的列表，只保留所需的行
        new_lines = []
        for line in lines:
            if not pattern.match(line.strip()):
                new_lines.append(line)

        # 确保只保留一行关于IP转发的配置
        new_lines.append('net.ipv4.ip_forward=1\n')
        new_lines.append('net.ipv6.conf.all.forwarding=1\n')

        # 写入更新后的内容回文件
        with open(file_path, 'w') as file:
            file.writelines(new_lines)

        print("IP forwarding lines cleaned successfully.")
    except Exception as e:
        print(f"Error cleaning IP forwarding lines: {e}")

# 指定 sysctl.conf 文件路径
clean_ip_forwarding('/etc/sysctl.conf')
