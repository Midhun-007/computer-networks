@echo off
wsl -d Ubuntu-22.04 bash -c "cd '$(wslpath -u '%CD%')' && source .venv/bin/activate && python python/scripts/train.py"
