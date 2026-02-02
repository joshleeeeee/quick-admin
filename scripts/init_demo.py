"""
Demo 模式初始化脚本
创建 SQLite 示例数据库，用于演示 Quick-Admin 功能
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "demo.db")


def init_demo_db():
    """初始化演示数据库"""
    
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 连接数据库（不存在则创建）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            role TEXT DEFAULT 'user',
            created_at TEXT,
            updated_at TEXT,
            remark TEXT
        )
    """)
    
    # 创建订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL UNIQUE,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            product_name TEXT,
            quantity INTEGER DEFAULT 1,
            created_at TEXT,
            paid_at TEXT,
            remark TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # 创建操作日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operation_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            target_table TEXT,
            target_id TEXT,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            created_at TEXT
        )
    """)
    
    # 创建配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT NOT NULL UNIQUE,
            config_value TEXT,
            description TEXT,
            updated_at TEXT
        )
    """)
    
    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        print("✅ Demo 数据库已存在，跳过初始化")
        conn.close()
        return
    
    # 插入示例用户
    users = [
        ("admin", "admin@example.com", "13800138000", "active", "admin", "系统管理员"),
        ("zhangsan", "zhangsan@example.com", "13800138001", "active", "user", "普通用户"),
        ("lisi", "lisi@example.com", "13800138002", "active", "user", "VIP用户"),
        ("wangwu", "wangwu@example.com", "13800138003", "inactive", "user", "已停用"),
        ("zhaoliu", "zhaoliu@example.com", "13800138004", "active", "editor", "编辑人员"),
    ]
    
    now = datetime.now()
    for i, (username, email, phone, status, role, remark) in enumerate(users):
        created = (now - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (username, email, phone, status, role, created_at, updated_at, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, phone, status, role, created, created, remark))
    
    # 插入示例订单
    products = ["iPhone 15", "MacBook Pro", "AirPods", "iPad", "Apple Watch"]
    statuses = ["pending", "paid", "shipped", "completed", "cancelled"]
    
    for i in range(20):
        order_no = f"ORD{now.strftime('%Y%m%d')}{str(i+1).zfill(4)}"
        user_id = random.randint(1, 5)
        amount = round(random.uniform(100, 10000), 2)
        status = random.choice(statuses)
        product = random.choice(products)
        quantity = random.randint(1, 3)
        created = (now - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S")
        paid = created if status in ["paid", "shipped", "completed"] else None
        
        cursor.execute("""
            INSERT INTO orders (order_no, user_id, amount, status, product_name, quantity, created_at, paid_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_no, user_id, amount, status, product, quantity, created, paid))
    
    # 插入示例配置
    configs = [
        ("site_name", "Quick-Admin Demo", "网站名称"),
        ("max_upload_size", "10485760", "最大上传大小(字节)"),
        ("enable_register", "true", "是否开放注册"),
        ("default_role", "user", "默认用户角色"),
        ("session_timeout", "3600", "会话超时时间(秒)"),
    ]
    
    for key, value, desc in configs:
        cursor.execute("""
            INSERT INTO configs (config_key, config_value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value, desc, now.strftime("%Y-%m-%d %H:%M:%S")))
    
    # 插入示例日志
    actions = ["login", "logout", "update", "delete", "create"]
    for i in range(50):
        user_id = random.randint(1, 5)
        action = random.choice(actions)
        created = (now - timedelta(hours=random.randint(0, 168))).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO operation_logs (user_id, action, target_table, created_at, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action, random.choice(["users", "orders", "configs"]), created, f"192.168.1.{random.randint(1, 255)}"))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Demo 数据库初始化完成: {DB_PATH}")
    print("   - 用户表: 5 条记录")
    print("   - 订单表: 20 条记录")
    print("   - 配置表: 5 条记录")
    print("   - 日志表: 50 条记录")


if __name__ == "__main__":
    init_demo_db()
