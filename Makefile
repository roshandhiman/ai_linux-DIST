VM_HOST ?= roshanpreet@10.211.55.12
REMOTE_DIR ?= /home/roshanpreet/distro-dev

.PHONY: live-sync live-desktop live-hud test-ai iso

# Build a live ISO on a Debian 13 host: make iso ISO=/absolute/path/MineOS.iso
iso:
	sudo bash scripts/build-iso.sh $(ISO)

live-sync:
	rsync -avz --exclude '.git' --exclude '.venv' --exclude '*.gguf' --exclude '*.iso' --exclude 'dist' ./ $(VM_HOST):$(REMOTE_DIR)/
	ssh $(VM_HOST) "sudo mkdir -p /opt/ai && sudo cp -r $(REMOTE_DIR)/ai/agent/* /opt/ai/ && sudo ln -sf /opt/ai/jarvis.py /usr/local/bin/ai && sudo ln -sf /opt/ai/jarvis_gui.py /usr/local/bin/ai-hud && sudo chmod +x /usr/local/bin/ai /usr/local/bin/ai-hud /opt/ai/*.py"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/desktop/ai.desktop /usr/share/applications/ && sudo chmod +x /usr/share/applications/ai.desktop"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/ai/system/ai-shell.sh /etc/profile.d/ && sudo chmod +x /etc/profile.d/ai-shell.sh"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/rootfs/etc/sysctl.d/99-ai-kernel.conf /etc/sysctl.d/ && sudo sysctl -p /etc/sysctl.d/99-ai-kernel.conf || true"
	ssh $(VM_HOST) "sudo mkdir -p /etc/udev/rules.d && sudo cp $(REMOTE_DIR)/ai/system/99-ai-hardware.rules /etc/udev/rules.d/ && sudo cp $(REMOTE_DIR)/ai/system/ai-hardware-event /usr/local/bin/ && sudo chmod +x /usr/local/bin/ai-hardware-event && sudo udevadm control --reload-rules || true"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/ai/system/ai-sentinel.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now ai-sentinel.service || true"

live-desktop:
	rsync -avz --exclude '__pycache__' desktop/ $(VM_HOST):/opt/ai/desktop/
	rsync -avz ai/agent/jarvis_gui.py ai/agent/research.py ai/agent/artifacts.py $(VM_HOST):/opt/ai/
	ssh $(VM_HOST) "chmod +x /opt/ai/desktop/*.sh /opt/ai/jarvis_gui.py && bash /opt/ai/desktop/apply-theme.sh"

live-hud:
	ssh $(VM_HOST) "DISPLAY=:0 python3 /opt/ai/jarvis_gui.py"

test-ai:
	ssh $(VM_HOST) "ai 'open files and check memory'"
