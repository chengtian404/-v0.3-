# Admin Module Quick Start

## After Starting the Server

1. Visit http://localhost:10010/admin/login
2. Login with: admin / 123456
3. You will see the admin dashboard with 4 management modules:

## Module Overview

### 1. User Management (/admin/users)
- View all users with pagination (20/page)
- Search users by username
- Add new users (assign to roles)
- Edit user role or reset password
- Enable/disable users
- Delete users
- The super admin (admin) cannot disable/delete themselves

### 2. Role Management (/admin/roles)
- View all roles with pagination
- Add custom roles
- Edit custom roles (system roles "System Admin" and "Normal User" are locked)
- Delete custom roles (only if no users are assigned)
- Assign function permissions via tree view

### 3. Function Management (/admin/functions)
- View all functions with pagination
- Add functions (top-level or child)
- Edit function details (name, icon, route, sort order, status)
- Enable/disable functions
- Delete functions (and their children)
- Functions can be organized in a 2-level hierarchy

### 4. Menu Management (/admin/menus)
- Select a role to preview its menu
- Reorder menu items with up/down buttons
- Save sort order
- Menus are auto-synced from role permissions

## Database
- SQLite (finderos.db) in the database/ directory
- Auto-created on first run
- Default roles and admin account are pre-seeded