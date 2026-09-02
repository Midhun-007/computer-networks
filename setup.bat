@echo off
wsl -d Ubuntu-22.04 bash -c "cd '$(wslpath -u '%CD%')' && chmod +x setup/install_ns3.sh && ./setup/install_ns3.sh"
