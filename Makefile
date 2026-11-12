VM_HOST ?= roshanpreet@10.211.55.12
REMOTE_DIR ?= /home/roshanpreet/distro-dev

.PHONY: live-sync live-hud test-ai git-push

live-sync:
	rsync -avz --exclude '.git' --exclude '*.gguf' --exclude '*.iso' ./ $(VM_HOST):$(REMOTE_DIR)/
	ssh $(VM_HOST) "sudo mkdir -p /opt/ai && sudo cp -r $(REMOTE_DIR)/ai-agent/* /opt/ai/ && sudo ln -sf /opt/ai/jarvis.py /usr/local/bin/ai && sudo ln -sf /opt/ai/jarvis_gui.py /usr/local/bin/ai-hud && sudo chmod +x /usr/local/bin/ai /usr/local/bin/ai-hud /opt/ai/jarvis.py /opt/ai/jarvis_gui.py"
	ssh $(VM_HOST) "sudo cp $(REMOTE_DIR)/desktop/ai.desktop /usr/share/applications/ && sudo chmod +x /usr/share/applications/ai.desktop"

live-hud:
	ssh $(VM_HOST) "DISPLAY=:0 python3 /opt/ai/jarvis_gui.py"

test-ai:
	ssh $(VM_HOST) "ai 'open files and check memory'"

git-push:
	git add .
	git commit -m "update core and ui"
	git push origin main
