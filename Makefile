VM_HOST ?= roshanpreet@10.211.55.12
REMOTE_DIR ?= /home/roshanpreet/jarvis-os

.PHONY: help live-sync live-hud test-ai git-push

help:
	@echo "JarvisOS Development Workflow:"
	@echo "  make live-sync    - Sync all files to live Debian VM"
	@echo "  make live-hud     - Launch Jarvis Spotlight HUD on VM display"
	@echo "  make test-ai      - Test Jarvis AI Agent CLI"
	@echo "  make git-push     - Commit & push changes to GitHub"

live-sync:
	@echo "Syncing code to Debian VM..."
	rsync -avz --exclude '.git' --exclude '*.gguf' --exclude '*.iso' ./ $(VM_HOST):$(REMOTE_DIR)/
	ssh $(VM_HOST) "sudo mkdir -p /opt/jarvis && sudo cp -r $(REMOTE_DIR)/ai-agent/* /opt/jarvis/ && sudo ln -sf /opt/jarvis/jarvis.py /usr/local/bin/jarvis && sudo chmod +x /usr/local/bin/jarvis"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/desktop/jarvis.desktop /usr/share/applications/ && sudo chmod +x /usr/share/applications/jarvis.desktop"

live-hud:
	ssh $(VM_HOST) "DISPLAY=:0 python3 /opt/jarvis/jarvis_gui.py"

test-ai:
	ssh $(VM_HOST) "jarvis 'open files and check battery status'"

git-push:
	git add .
	git commit -m "Update JarvisOS core and UI features"
	git push origin main
