#!/bin/bash

# 定义sshd配置文件路径
SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP_PATH="/etc/ssh/sshd_config.bak"

# 备份当前配置文件
echo "备份当前的sshd配置文件到 $BACKUP_PATH"
sudo cp $SSHD_CONFIG $BACKUP_PATH

# 解锁root用户
if sudo passwd -S root | grep -q "L"; then
    echo "发现root账户被锁定，正在解锁..."
    sudo passwd -u root
    echo "请设置root用户密码："
    sudo passwd root
fi

# 检查并修改PermitRootLogin设置
if sudo grep -q "^#PermitRootLogin prohibit-password" $SSHD_CONFIG; then
    echo "找到被注释掉的 PermitRootLogin prohibit-password，正在修改..."
    sudo sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/' $SSHD_CONFIG
elif sudo grep -q "^PermitRootLogin prohibit-password" $SSHD_CONFIG; then
    echo "找到未注释的 PermitRootLogin prohibit-password，正在修改..."
    sudo sed -i 's/^PermitRootLogin prohibit-password/PermitRootLogin yes/' $SSHD_CONFIG
else
    echo "没有找到 'PermitRootLogin prohibit-password'，在文件末尾添加 'PermitRootLogin yes'..."
    echo "PermitRootLogin yes" | sudo tee -a $SSHD_CONFIG
fi

# 重启SSH服务以应用更改
echo "重启SSH服务..."
sudo systemctl restart ssh

echo "完成！root登录已经启用。"

