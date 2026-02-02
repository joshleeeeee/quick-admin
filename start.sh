#!/bin/bash
# Quick-Admin 启动脚本

# 设置 Oracle Instant Client 路径
export DYLD_LIBRARY_PATH=/opt/oracle/instantclient_23_3:$DYLD_LIBRARY_PATH

# 启动应用
cd "$(dirname "$0")"
streamlit run app.py "$@"
