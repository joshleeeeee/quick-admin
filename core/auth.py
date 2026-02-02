"""
认证模块
提供简单的密码登录验证功能
"""

import hashlib
import os
from typing import Tuple

import streamlit as st


# 默认管理员密码（实际使用时应该从环境变量或配置文件读取）
# 这里使用 SHA256 哈希存储密码
# 默认密码: admin123
DEFAULT_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()


def get_password_hash() -> str:
    """
    获取密码哈希值
    优先从环境变量读取，否则使用默认值
    
    Returns:
        密码哈希值
    """
    # 可以从环境变量设置密码哈希
    env_hash = os.environ.get("INSTANT_ADMIN_PASSWORD_HASH")
    if env_hash:
        return env_hash
    
    # 也可以从环境变量设置明文密码（会自动转换为哈希）
    env_password = os.environ.get("INSTANT_ADMIN_PASSWORD")
    if env_password:
        return hashlib.sha256(env_password.encode()).hexdigest()
    
    return DEFAULT_PASSWORD_HASH


def verify_password(password: str) -> bool:
    """
    验证密码是否正确
    
    Args:
        password: 用户输入的密码
        
    Returns:
        密码是否正确
    """
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == get_password_hash()


def check_authentication() -> bool:
    """
    检查用户是否已认证
    
    Returns:
        是否已认证
    """
    return st.session_state.get("authenticated", False)


def login() -> None:
    """
    显示登录界面并处理登录逻辑
    """
    # 设置页面标题
    st.markdown(
        """
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .login-title {
            text-align: center;
            color: white;
            font-size: 2em;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }
        .login-subtitle {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            font-size: 1em;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # 居中显示登录表单
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 Quick-Admin")
        st.markdown("##### 数据库管理工具")
        st.markdown("---")
        
        # 登录表单
        with st.form("login_form"):
            password = st.text_input(
                "管理密码",
                type="password",
                placeholder="请输入管理密码",
            )
            
            submitted = st.form_submit_button(
                "登 录",
                use_container_width=True,
            )
            
            if submitted:
                if verify_password(password):
                    st.session_state["authenticated"] = True
                    st.success("✅ 登录成功！")
                    st.rerun()
                else:
                    st.error("❌ 密码错误，请重试")
        
        st.markdown("---")
        st.caption("💡 默认密码: admin123")
        st.caption("🔧 可通过环境变量 INSTANT_ADMIN_PASSWORD 自定义密码")


def logout() -> None:
    """
    执行登出操作
    """
    st.session_state["authenticated"] = False
    st.rerun()


def require_auth(func):
    """
    装饰器：要求认证后才能访问
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    def wrapper(*args, **kwargs):
        if not check_authentication():
            login()
            return None
        return func(*args, **kwargs)
    return wrapper
