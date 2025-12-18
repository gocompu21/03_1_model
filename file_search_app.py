import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from fileSearchStore import GeminiStoreManager
import os
import time
import markdown
from tkhtmlview import HTMLText

# Theme Colors
COLORS = {
    "sidebar": "#1b4332",
    "bg": "#f0f7f4",
    "user_bg": "#e8f5e9",
    "user_border": "#2d6a4f",
    "ai_bg": "#ffffff",
    "ai_border": "#40916c",
    "text": "#333333",
    "btn": "#2d6a4f",
    "btn_hover": "#1b4332",
    "accent": "#40916c",
}

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 나무의사 채팅")
        self.geometry("1100x700")

        # Configure Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Initialize Logic
        self.default_key = os.environ.get("GEMINI_API_KEY", "")
        self.store_manager = GeminiStoreManager(api_key=self.default_key)
        self.current_stores = []

        self.setup_sidebar()
        self.setup_main_area()

        # Load stores initially
        self.refresh_store_list()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=250, corner_radius=0, fg_color=COLORS["sidebar"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        logo_label = ctk.CTkLabel(
            self.sidebar,
            text="AI 나무의사",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white",
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Store Management
        ctk.CTkLabel(
            self.sidebar, text="지식 관리", text_color="#95d5b2", anchor="w"
        ).grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.entry_store_name = ctk.CTkEntry(
            self.sidebar, placeholder_text="New Store Name"
        )
        self.entry_store_name.grid(row=2, column=0, padx=20, pady=5)

        ctk.CTkButton(
            self.sidebar,
            text="Create Store",
            command=self.create_new_store,
            fg_color=COLORS["accent"],
            hover_color=COLORS["btn_hover"],
        ).grid(row=3, column=0, padx=20, pady=5)

        # File Management
        ctk.CTkLabel(
            self.sidebar, text="파일 관리", text_color="#95d5b2", anchor="w"
        ).grid(row=5, column=0, padx=20, pady=(20, 0), sticky="w")

        ctk.CTkButton(
            self.sidebar,
            text="Upload Files",
            command=self.upload_files,
            fg_color=COLORS["accent"],
            hover_color=COLORS["btn_hover"],
        ).grid(row=6, column=0, padx=20, pady=5)
        ctk.CTkButton(
            self.sidebar,
            text="Delete File",
            command=self.open_delete_window,
            fg_color="#e63946",
            hover_color="#d62828",
        ).grid(row=7, column=0, padx=20, pady=10)

        # API Key
        self.entry_api_key = ctk.CTkEntry(
            self.sidebar, placeholder_text="API Key (Optional)"
        )
        self.entry_api_key.insert(0, self.default_key)
        self.entry_api_key.grid(row=8, column=0, padx=20, pady=20, sticky="s")

    def setup_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header
        self.store_select = ctk.CTkComboBox(
            self.main_frame,
            values=["Select Store"],
            width=300,
            fg_color="white",
            text_color="black",
            button_color=COLORS["btn"],
        )
        self.store_select.grid(row=0, column=0, padx=20, pady=20)

        # Chat Area
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.main_frame, fg_color=COLORS["bg"]
        )
        self.chat_scroll.grid(row=1, column=0, padx=40, pady=(0, 20), sticky="nsew")

        # Input Area
        self.input_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_container.grid(row=2, column=0, padx=40, pady=20, sticky="ew")

        self.chat_input = ctk.CTkEntry(
            self.input_container,
            placeholder_text="질문을 입력하세요...",
            height=50,
            font=ctk.CTkFont(size=14),
            border_color=COLORS["btn"],
            fg_color="white",
            text_color="black",
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_input.bind("<Return>", lambda e: self.send_message())

        self.btn_send = ctk.CTkButton(
            self.input_container,
            text="보내기",
            width=100,
            height=50,
            fg_color=COLORS["btn"],
            hover_color=COLORS["btn_hover"],
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.send_message,
        )
        self.btn_send.pack(side="right")

        # Overlay for Progress
        self.progress_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="white",
            border_color=COLORS["user_border"],
            border_width=1,
            width=250,
            height=60,
        )
        # We don't grid it initially, we place it when needed

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="답변 생성 중... 0.0s",
            text_color=COLORS["btn"],
            font=ctk.CTkFont(weight="bold"),
        )
        self.progress_label.place(relx=0.5, rely=0.3, anchor="center")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, width=200, height=4, progress_color=COLORS["accent"]
        )
        self.progress_bar.place(relx=0.5, rely=0.7, anchor="center")
        self.progress_bar.set(0)

    # --- Logic ---

    def create_new_store(self):
        name = self.entry_store_name.get()
        if not name:
            return
        if self.store_manager.create_store(name):
            messagebox.showinfo("Success", f"Store '{name}' created!")
            self.refresh_store_list()
            self.entry_store_name.delete(0, "end")

    def upload_files(self):
        # First ensure a store is selected or created?
        # Actually current system allows uploading fully to standard list?
        # SDK Limitation: We upload generally, then associate.
        # But UI flow requires selecting files.
        files = filedialog.askopenfilenames()
        if not files:
            return

        # Auto-create store if "Select Store" or empty
        current_store = (
            self.store_select.get()
            if self.store_select.get() != "Select Store"
            else "Default Store"
        )

        # Using Thread
        def run_upload():
            self.store_manager.create_store_with_files(
                current_store, [f for f in files]
            )
            self.refresh_store_list()

        threading.Thread(target=run_upload, daemon=True).start()
        messagebox.showinfo("Info", "File upload started in background.")

    def refresh_store_list(self):
        # Update combo box
        stores = list(self.store_manager.stores.keys())
        self.store_select.configure(values=stores)
        if stores:
            self.store_select.set(stores[0])

    def open_delete_window(self):
        # Simplified: Just ask for name or list all files
        # For now, just show info
        messagebox.showinfo("Info", "Manage files via code for now or select store.")

    def send_message(self):
        msg = self.chat_input.get()
        dn = self.store_select.get()

        if not msg or not dn or dn == "Select Store":
            messagebox.showwarning(
                "Warning", "Please select a store and enter a message."
            )
            return

        store_id = dn  # Using name as ID for virtual stores

        self.chat_input.delete(0, "end")
        self.add_message(msg, is_user=True)

        # Show Progress
        self.show_progress(True)
        self.start_time = time.time()
        self.update_timer()

        def run():
            try:
                resp = self.store_manager.query_store(store_id, msg)
                self.after(0, lambda: self.handle_response(resp))
            except Exception as e:
                self.after(0, lambda: self.handle_response(f"Error: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def show_progress(self, show):
        if show:
            self.progress_frame.place(relx=0.5, rely=0.85, anchor="center")
            self.progress_bar.start()
            self.progress_active = True
        else:
            self.progress_frame.place_forget()
            self.progress_bar.stop()
            self.progress_active = False

    def update_timer(self):
        if hasattr(self, "progress_active") and self.progress_active:
            elapsed = time.time() - self.start_time
            self.progress_label.configure(text=f"답변 생성 중... {elapsed:.1f}s")
            self.after(100, self.update_timer)

    def handle_response(self, text):
        self.show_progress(False)
        self.add_message(text, is_user=False)

    def add_message(self, text, is_user):
        # Bubble Frame
        bg_color = COLORS["user_bg"] if is_user else COLORS["ai_bg"]
        border_color = COLORS["user_border"] if is_user else COLORS["ai_border"]

        # Outer Frame (for margin)
        outer = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        outer.pack(fill="x", pady=10)

        # Bubble
        bubble = ctk.CTkFrame(
            outer,
            fg_color=bg_color,
            corner_radius=10,
            border_color=border_color if is_user else None,
            border_width=1 if is_user else 0,
        )
        # AI bubble has left border bar style
        # User bubble is green box

        # Alignment
        if is_user:
            bubble.pack(side="right", padx=(50, 10))  # Margin left
            # Header
            ctk.CTkLabel(
                bubble,
                text="질문:",
                font=ctk.CTkFont(weight="bold", size=12),
                text_color="#2d6a4f",
                anchor="w",
            ).pack(fill="x", padx=15, pady=(10, 0))
        else:
            bubble.pack(side="left", padx=(10, 50))  # Margin right
            # Left Bar simulation for AI bubble?
            # We can use a colored frame inside
            left_bar = ctk.CTkFrame(
                bubble, width=5, fg_color=COLORS["ai_border"], corner_radius=0
            )
            left_bar.pack(side="left", fill="y", padx=(0, 10))

            # Content container (right of bar)
            content_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            content_frame.pack(side="left", fill="both", expand=True)

            # Header
            ctk.CTkLabel(
                content_frame,
                text="나무주치의 답변:",
                font=ctk.CTkFont(weight="bold", size=12),
                text_color="#1b4332",
                anchor="w",
            ).pack(fill="x", padx=10, pady=(10, 0))

        # Content Text (HTMLText)
        # Prepare HTML
        target_frame = bubble if is_user else content_frame

        try:
            if is_user:
                # User: Simple text, Selectable
                safe_text = text.replace("\n", "<br>")
                styled_html = f"""
                <div style="font-family: 'Noto Sans KR', sans-serif; color: #333; font-size: 14px; line-height: 1.5;">
                    {safe_text}
                </div>
                """
                lbl = HTMLText(
                    target_frame,
                    html=styled_html,
                    background=bg_color,
                    foreground="#333",
                    height=1,
                )
            else:
                # AI: Markdown
                html_content = markdown.markdown(
                    text, extensions=["fenced_code", "tables"]
                )
                # Tags Fix
                html_content = html_content.replace("<strong>", "<b>").replace(
                    "</strong>", "</b>"
                )
                html_content = html_content.replace("<em>", "<i>").replace(
                    "</em>", "</i>"
                )
                html_content = html_content.replace("<h1>", "<h3>").replace(
                    "<h2>", "<h4>"
                )
                # Bullets Fix
                html_content = html_content.replace("<ul>", "").replace("</ul>", "")
                html_content = html_content.replace("<li>", "<br>&bull; ").replace(
                    "</li>", ""
                )

                styled_html = f"""
                <div style="font-family: 'Noto Sans KR', sans-serif; color: #333; font-size: 14px; line-height: 1.6;">
                    {html_content}
                </div>
                """
                lbl = HTMLText(
                    target_frame,
                    html=styled_html,
                    background=bg_color,
                    foreground="#333",
                    height=1,
                )

            lbl.pack(padx=10, pady=10, fill="both", expand=True)
            lbl.fit_height()

            # Key bindings
            lbl.bind("<Key>", lambda e: "break")  # No typing
            lbl.bind("<Control-c>", lambda e: None)  # Allow copy

        except Exception as e:
            ctk.CTkLabel(target_frame, text=f"Error: {e}").pack()

        self.after(100, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        try:
            self.chat_scroll._parent_canvas.yview_moveto(1.0)
        except:
            pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
