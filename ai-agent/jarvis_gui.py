#!/usr/bin/env python3
import tkinter as tk
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jarvis

class SpotlightHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("AI HUD")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0f141c")

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = 680
        h = 130
        x = (screen_w - w) // 2
        y = screen_h // 4
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.container = tk.Frame(self.root, bg="#131924", bd=2, relief="solid", highlightbackground="#00e5ff", highlightthickness=1)
        self.container.pack(fill="both", expand=True, padx=4, pady=4)

        self.header_frame = tk.Frame(self.container, bg="#131924")
        self.header_frame.pack(fill="x", padx=15, pady=(10, 5))

        self.icon_label = tk.Label(self.header_frame, text="AI CORE", font=("Segoe UI", 9, "bold"), fg="#00e5ff", bg="#131924")
        self.icon_label.pack(side="left")

        self.model_label = tk.Label(self.header_frame, text=f"[{jarvis.get_active_model()}]", font=("Segoe UI", 8), fg="#718096", bg="#131924")
        self.model_label.pack(side="right")

        self.entry_frame = tk.Frame(self.container, bg="#1b2434", bd=1, relief="flat")
        self.entry_frame.pack(fill="x", padx=15, pady=5)

        self.prompt_symbol = tk.Label(self.entry_frame, text="❯", font=("Segoe UI", 12, "bold"), fg="#00e5ff", bg="#1b2434", padx=8)
        self.prompt_symbol.pack(side="left")

        self.entry = tk.Entry(self.entry_frame, font=("Segoe UI", 12), bg="#1b2434", fg="#ffffff", insertbackground="#00e5ff", bd=0, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        self.entry.focus_set()

        self.status_label = tk.Label(self.container, text="Type a command, open apps, control ESP32, or ask a question...", font=("Segoe UI", 9), fg="#94a3b8", bg="#131924", anchor="w")
        self.status_label.pack(fill="x", padx=18, pady=(4, 10))

        self.root.bind("<Return>", self.on_submit)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def on_submit(self, event=None):
        query = self.entry.get().strip()
        if not query:
            return

        self.status_label.config(text="Thinking...", fg="#00e5ff")
        self.entry.config(state="disabled")

        def run_in_background():
            action_data = jarvis.query_llm(query)
            res = jarvis.execute_action(action_data)
            self.root.after(0, lambda: self.update_result(res))

        threading.Thread(target=run_in_background, daemon=True).start()

    def update_result(self, response_text):
        self.status_label.config(text=response_text[:90] + ("..." if len(response_text) > 90 else ""), fg="#e2e8f0")
        self.entry.config(state="normal")
        self.entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotlightHUD(root)
    root.mainloop()
