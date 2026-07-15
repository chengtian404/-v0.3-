"""
make_admin.py -- Create default admin account
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.user import UserRepository
from app.models.db import init_db

init_db()

username = "admin"
password = "123456"

if UserRepository.create_user(username, password, role_id=1):
    print("=" * 40)
    print("  Admin account created!")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print("=" * 40)
else:
    print("Admin account already exists.")