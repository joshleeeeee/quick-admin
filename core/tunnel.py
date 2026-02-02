"""
隧道管理模块
集成 ngrok 实现内网穿透
"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from pyngrok import conf, ngrok
import streamlit as st


def _load_tunnel_config() -> dict:
    """加载穿透配置"""
    config_dir = Path(__file__).parent.parent / "configs"
    
    # 优先读取 tunnel.yaml
    config_file = config_dir / "tunnel.yaml"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
            
    # 否则读取 example（通常是禁用的）
    example_file = config_dir / "tunnel.example.yaml"
    if example_file.exists():
        with open(example_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
            
    return {}


def start_tunnel(port: int = 8501) -> Optional[str]:
    """
    启动内网穿透
    
    Args:
        port: 本地服务端口
    
    Returns:
        公网 URL，如果未启用或失败则返回 None
    """
    # 1. 检查配置
    config = _load_tunnel_config()
    
    # 支持环境变量覆盖
    enable = os.environ.get("QUICK_ADMIN_TUNNEL_ENABLE")
    if enable:
        enable = enable.lower() == "true"
    else:
        enable = config.get("enable", False)
        
    if not enable:
        return None
        
    # 2. 检查是否已经存在隧道（防止 Streamlit 重载时重复创建）
    # Streamlit 的 session state 在 reruns 之间可以保持，但最好检查实际隧道列表
    try:
        tunnels = ngrok.get_tunnels()
        if tunnels:
            for t in tunnels:
                # 如果已经有一个隧道指向这个端口，直接返回
                if str(port) in t.config.get("addr", ""):
                    return t.public_url
    except Exception:
        pass

    # 3. 设置 Authtoken
    token = os.environ.get("QUICK_ADMIN_NGROK_TOKEN") or config.get("auth_token")
    if token:
        conf.get_default().auth_token = token
    
    # 设置区域
    region = config.get("region")
    if region:
        conf.get_default().region = region

    # 4. 确定端口
    # 默认 8501，优先尝试从命令行参数获取
    port = 8501
    
    # 尝试从命令行参数获取端口 (streamlit run app.py --server.port 8502)
    try:
        # Streamlit 可能会过滤掉部分参数，这里尽力尝试获取
        for i, arg in enumerate(sys.argv):
            if arg in ["--server.port", "--port"] and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
                break
    except Exception:
        pass
    
    # 5. 启动隧道
    try:
        # 这里的 port 默认为 8501，或从命令行解析
        public_url = ngrok.connect(port, config.get("protocol", "http")).public_url
        
        # 在终端打印，方便查看
        print(f"\n{'='*40}")
        print(f"🌏 Ngrok Tunnel Active: {public_url}")
        print(f"   Forwarding to: http://localhost:{port}")
        print(f"{'='*40}\n")
        
        return public_url
    except Exception as e:
        print(f"\n❌ Ngrok 连接失败: {e}\n", file=sys.stderr)
        return None
