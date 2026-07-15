"""
user_case.py — UserRepository 功能测试用例

测试用户数据访问层核心功能:
- 创建用户 / 重复创建检测
- 密码验证 / 错误密码 / 不存在用户
- 用户计数 & 列表查询
- 用户状态切换
- 密码修改
- 删除用户
"""

import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.db import init_db
from app.models.user import UserRepository

init_db()

test_user = f"testuser_{int(time.time())}"
test_password = "test123456"

print("=" * 50)
print("  UserRepository 功能测试用例")
print("=" * 50)

# [1] 新建用户
r1 = UserRepository.create_user(test_user, test_password)
print(f"[1] 新建用户 '{test_user}': {'PASS' if r1 else 'FAIL'} (应为 True)")

# [2] 重复创建
r2 = UserRepository.create_user(test_user, test_password)
print(f"[2] 重复创建: {'PASS' if not r2 else 'FAIL'} (应为 False)")

# [3] 验证正确密码
r3 = UserRepository.verify_user(test_user, test_password)
print(f"[3] 验证正确密码: {'PASS' if r3 else 'FAIL'} (应为 True)")

# [4] 验证错误密码
r4 = UserRepository.verify_user(test_user, "wrongpassword")
print(f"[4] 验证错误密码: {'PASS' if not r4 else 'FAIL'} (应为 False)")

# [5] 验证不存在用户
r5 = UserRepository.verify_user("nonexistent_xyz", test_password)
print(f"[5] 验证不存在用户: {'PASS' if not r5 else 'FAIL'} (应为 False)")

# [6] 获取用户总数
count = UserRepository.get_user_count()
r6 = count > 0
print(f"[6] 用户总数 >= 1: {'PASS' if r6 else 'FAIL'} (当前: {count})")

# [7] 获取用户列表
users = UserRepository.get_all_users(page=1, page_size=10)
r7 = len(users) > 0
print(f"[7] 获取用户列表: {'PASS' if r7 else 'FAIL'} (共 {len(users)} 条)")

# [8] 查询指定用户
user = UserRepository.get_user_by_username(test_user)
r8 = user is not None and user["username"] == test_user
print(f"[8] 查询指定用户: {'PASS' if r8 else 'FAIL'}")

# [9] 切换用户状态
status_before = user["status"]
UserRepository.toggle_user_status(test_user)
user_after = UserRepository.get_user_by_username(test_user)
r9 = user_after["status"] != status_before
print(f"[9] 切换用户状态: {'PASS' if r9 else 'FAIL'} ({status_before} -> {user_after['status']})")

UserRepository.toggle_user_status(test_user)  # 恢复

# [10] 修改密码
r10 = UserRepository.change_password(test_user, test_password, "newpassword456")
print(f"[10] 修改密码: {'PASS' if r10 else 'FAIL'} (应为 True)")

r10b = UserRepository.verify_user(test_user, "newpassword456")
print(f"[10b] 验证新密码: {'PASS' if r10b else 'FAIL'} (应为 True)")

# [11] 删除用户
r11 = UserRepository.delete_user(test_user)
print(f"[11] 删除测试用户: {'PASS' if r11 else 'FAIL'} (应为 True)")

print("=" * 50)
print("  用例执行完成")
print("=" * 50)
