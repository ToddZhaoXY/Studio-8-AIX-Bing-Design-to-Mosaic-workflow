#!/bin/zsh
cd "$(dirname "$0")" || exit 1
python3 tools/mosaic-workbench/launch.py
if [[ $? -ne 0 ]]; then
  read -k 1 '?按任意键关闭…'
fi
