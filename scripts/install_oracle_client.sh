#!/bin/bash
# Oracle Instant Client 安装脚本 (macOS ARM)

set -e

INSTALL_DIR="/opt/oracle/instantclient_19_8"
DMG_URL="https://download.oracle.com/otn_software/mac/instantclient/198000/instantclient-basic-macos.arm64-19.8.0.0.0dbru.dmg"

echo "=========================================="
echo "Oracle Instant Client 安装脚本"
echo "=========================================="
echo ""

# 检查是否已安装
if [ -f "$INSTALL_DIR/libclntsh.dylib" ]; then
    echo "✅ Instant Client 已安装在 $INSTALL_DIR"
    echo ""
    echo "请确保环境变量已设置："
    echo "  export DYLD_LIBRARY_PATH=$INSTALL_DIR:\$DYLD_LIBRARY_PATH"
    exit 0
fi

echo "⚠️  需要手动下载 Instant Client（Oracle 要求登录）"
echo ""
echo "步骤 1: 打开浏览器下载:"
echo "  https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html"
echo ""
echo "  下载: instantclient-basic-macos.arm64-19.8.0.0.0dbru.dmg (约75MB)"
echo ""
echo "步骤 2: 下载完成后，运行以下命令安装:"
echo ""
echo "  # 挂载 DMG"
echo "  hdiutil attach ~/Downloads/instantclient-basic-macos.arm64-19.8.0.0.0dbru.dmg"
echo ""
echo "  # 创建目录并复制"
echo "  sudo mkdir -p /opt/oracle"
echo "  sudo cp -r /Volumes/instantclient-basic-macos.arm64-19.8.0.0.0dbru/instantclient_19_8 /opt/oracle/"
echo ""
echo "  # 卸载 DMG"
echo "  hdiutil detach /Volumes/instantclient-basic-macos.arm64-19.8.0.0.0dbru"
echo ""
echo "步骤 3: 设置环境变量:"
echo ""
echo "  echo 'export DYLD_LIBRARY_PATH=/opt/oracle/instantclient_19_8:\$DYLD_LIBRARY_PATH' >> ~/.zshrc"
echo "  source ~/.zshrc"
echo ""
echo "步骤 4: 重启应用:"
echo ""
echo "  streamlit run app.py"
echo ""
