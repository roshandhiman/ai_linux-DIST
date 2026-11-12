#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import threading
import sys
import os
import fcntl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jarvis

LOCK_FILE = "/tmp/ai_hud.lock"
try:
    lock_fd = open(LOCK_FILE, "w")
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, BlockingIOError):
    sys.exit(0)

class ChatHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Assistant")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#0c0e14")
        self.root.resizable(False, False)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = 460
        h = 580
        x = (screen_w - w) // 2
        y = (screen_h - h) // 3
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.border_frame = tk.Frame(self.root, bg="#1a202c", bd=1)
        self.border_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.main_frame = tk.Frame(self.border_frame, bg="#0f131a")
        self.main_frame.pack(fill="both", expand=True)

        self.header = tk.Frame(self.main_frame, bg="#0f131a", height=38)
        self.header.pack(fill="x", padx=14, pady=(10, 5))
        self.header.pack_propagate(False)

        self.dot = tk.Label(self.header, text="●", font=("Segoe UI", 10), fg="#00f2fe", bg="#0f131a")
        self.dot.pack(side="left")

        self.title_lbl = tk.Label(self.header, text="AI Assistant", font=("Segoe UI", 10, "bold"), fg="#e2e8f0", bg="#0f131a", padx=6)
        self.title_lbl.pack(side="left")

        self.chat_canvas = tk.Canvas(self.main_frame, bg="#0f131a", bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.chat_canvas.yview)
        self.scrollable_frame = tk.Frame(self.chat_canvas, bg="#0f131a")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        )

        self.canvas_window = self.chat_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=440)
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.chat_canvas.pack(fill="both", expand=True, padx=12, pady=5)

        self.input_container = tk.Frame(self.main_frame, bg="#161b24", bd=1, relief="solid", highlightbackground="#2d3748", highlightthickness=1)
        self.input_container.pack(fill="x", padx=12, pady=(5, 12))

        self.entry = tk.Entry(self.input_container, font=("Segoe UI", 11), bg="#161b24", fg="#f8fafc", insertbackground="#00f2fe", bd=0, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=10)

        self.send_btn = tk.Label(self.input_container, text="↵", font=("Segoe UI", 12, "bold"), fg="#00f2fe", bg="#161b24", cursor="hand2", padx=10)
        self.send_btn.pack(side="right")
        self.send_btn.bind("<Button-1>", lambda e: self.on_send())

        self.root.bind("<Return>", lambda e: self.on_send())
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.root.after(100, self.focus_entry)
        self.add_message("assistant", "Hello! How can I help you today?")

    def focus_entry(self):
        self.root.focus_force()
        self.entry.focus_set()
        self.entry.focus_force()

    def close(self):
        self.root.destroy()
        sys.exit(0)

    def add_message(self, sender, text, detail=None):
        msg_box = tk.Frame(self.scrollable_frame, bg="#0f131a", pady=4)
        msg_box.pack(fill="x", expand=True)

        if sender == "user":
            bubble = tk.Label(
                msg_box,
                text=text,
                font=("Segoe UI", 10),
                fg="#ffffff",
                bg="#1e293b",
                wraplength=340,
                justify="left",
                padx=10,
                pady=6
            )
            bubble.pack(side="right", padx=(40, 6))
        else:
            bubble = tk.Label(
                msg_box,
                text=text,
                font=("Segoe UI", 10),
                fg="#f1f5f9",
                bg="#151d2a",
                wraplength=340,
                justify="left",
                padx=10,
                pady=6
            )
            bubble.pack(side="left", padx=(6, 40))

            if detail:
                action_lbl = tk.Label(
                    msg_box,
                    text=f"↳ {detail}",
                    font=("Segoe UI", 8),
                    fg="#38bdf8",
                    bg="#0f131a",
                    padx=10
                )
                action_lbl.pack(side="left", fill="x", padx=(6, 40), pady=(2, 0))

        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def on_send(self):
        query = self.entry.get().strip()
        if not query:
            return

        self.entry.delete(0, tk.END)
        self.add_message("user", query)
        self.entry.config(state="disabled")

        def task():
            action_data = jarvis.query_llm(query)
            res = jarvis.execute_action(action_data)
            self.root.after(0, lambda: self.finish_response(res))

        threading.Thread(target=task, daemon=True).start()

    def finish_response(self, res):
        self.add_message("assistant", res.get("response", ""), res.get("detail"))
        self.entry.config(state="normal")
        self.focus_entry()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatHUD(root)
    root.mainloop()
