#!/bin/bash
# install.sh

INSTALL_DIR="/usr/local/bin"

# 复制主程序
sudo cp kei.py "$INSTALL_DIR/kei"
sudo chmod +x "$INSTALL_DIR/kei"

sudo cp repl.py "$INSTALL_DIR/repl"
sudo chmod +x "$INSTALL_DIR/repl"

sudo mkdir -p /usr/local/lib/keilang
sudo cp -r lib /usr/local/lib/keilang/

echo "Installed KeiLang 🥳"
echo "Use \"kei\" command"