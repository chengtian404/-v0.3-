#!/bin/bash
# ===================================================
#  DataFinderAgentOS 快速启动脚本 (Linux / macOS)
#  瞭望与问数系统 v0.1
# ===================================================

echo -e "\033[36m======================================\033[0m"
echo -e "\033[36m  瞭望与问数系统 (DataFinderAgentOS)\033[0m"
echo -e "\033[36m  快速启动脚本 v0.1\033[0m"
echo -e "\033[36m======================================\033[0m"

# 1. 检查虚拟环境
if [ ! -f "./venv/bin/activate" ]; then
    echo -e "\033[33m[1/4] 创建 Python 虚拟环境...\033[0m"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "\033[31m错误: 创建虚拟环境失败，请确认已安装 Python 3.11+\033[0m"
        exit 1
    fi
else
    echo -e "\033[32m[1/4] 虚拟环境已存在，跳过创建\033[0m"
fi

# 2. 激活虚拟环境并安装依赖
echo -e "\033[33m[2/4] 激活虚拟环境并安装依赖...\033[0m"
source ./venv/bin/activate
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo -e "\033[31m错误: 依赖安装失败\033[0m"
    exit 1
fi

# 3. 初始化管理员账号
echo -e "\033[33m[3/4] 初始化管理员账号...\033[0m"
python make_admin.py

# 4. 启动服务
echo -e "\033[33m[4/4] 启动 Tornado 服务...\033[0m"
echo ""
echo -e "\033[32m  前台入口: http://localhost:10010/\033[0m"
echo -e "\033[32m  后台入口: http://localhost:10010/admin/\033[0m"
echo -e "\033[32m  管理员账号: admin / 123456\033[0m"
echo ""
python app.py
