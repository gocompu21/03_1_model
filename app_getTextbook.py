import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pandas as pd
from datetime import datetime

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from exam.models import Question, Exam
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION


class TextbookGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Textbook Generator (기본서 해설 생성기)")
        self.root.geometry("600x600")

        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.manager = None
        self.is_running = False

        self._setup_ui()
        self._init_manager()

    def _init_manager(self):
        try:
            self.manager = GeminiStoreManager(api_key=self.api_key)
            self.log("Gemini Manager Initialized.")
        except Exception as e:
            self.log(f"Error initializing Gemini Manager: {e}")

    def _setup_ui(self):
        # Frame: Controls
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)

        # Exam Selection
        ttk.Label(control_frame, text="Select Exam Round:").pack(side="left", padx=5)
        self.exam_combo = ttk.Combobox(control_frame, state="readonly")
        self.exam_combo.pack(side="left", padx=5)
        self.load_exams()

        # Buttons
        self.start_btn = ttk.Button(
            control_frame, text="Start Generation", command=self.start_generation
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(
            control_frame, text="Stop", command=self.stop_generation, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            self.root, variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill="x", padx=10, pady=5)

        # Status Label
        self.status_lbl = ttk.Label(self.root, text="Ready")
        self.status_lbl.pack(anchor="w", padx=10)

        # Log Area
        self.log_area = scrolledtext.ScrolledText(
            self.root, state="disabled", height=20
        )
        self.log_area.pack(fill="both", expand=True, padx=10, pady=5)

    def load_exams(self):
        try:
            exams = Exam.objects.all().order_by("round_number")
            values = [f"{e.round_number}회" for e in exams]
            self.exam_combo["values"] = values
            if values:
                self.exam_combo.current(0)
        except Exception as e:
            self.log(f"Failed to load exams: {e}")

    def log(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert(
            "end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n"
        )
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def start_generation(self):
        if not self.manager:
            messagebox.showerror("Error", "Gemini Manager not initialized.")
            return

        selection = self.exam_combo.get()
        if not selection:
            messagebox.showwarning("Warning", "Please select an exam.")
            return

        round_num = int(selection.replace("회", ""))
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        thread = threading.Thread(target=self.run_process, args=(round_num,))
        thread.daemon = True
        thread.start()

    def stop_generation(self):
        self.is_running = False
        self.log("Stopping...")
        self.stop_btn.config(state="disabled")

    def run_process(self, round_num):
        try:
            questions = Question.objects.filter(exam__round_number=round_num).order_by(
                "number"
            )
            total = questions.count()
            results_data = []

            self.log(f"Found {total} questions for Exam {round_num}회.")

            # Define filename for incremental saving
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_{round_num}회_{timestamp_str}.xlsx"
            self.log(f"Saving results to {filename}")

            for i, q in enumerate(questions):
                if not self.is_running:
                    break

                store_name = q.subject.name
                # Construct Prompt
                prompt_content = (
                    f"{q.number}. {q.content}\n"
                    f"① {q.choice1}\n"
                    f"② {q.choice2}\n"
                    f"③ {q.choice3}\n"
                    f"④ {q.choice4}\n"
                    f"⑤ {q.choice5}"
                )

                # Apply System Instruction strictly
                prompt = f"{SYSTEM_INSTRUCTION}\n\n[문제]\n{prompt_content}"

                self.log(
                    f"--- [Q{q.number}] Prompt ---\n{prompt}\n-----------------------"
                )

                # Retry logic for Rate Limits
                max_retries = 5
                retry_delay = 30
                response_text = ""
                success = False
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                start_time = time.time()
                duration = 0

                for attempt in range(max_retries):
                    response_text = self.manager.query_store(store_name, prompt)

                    if (
                        "429" in response_text
                        or "Quota exceeded" in response_text
                        or "Resource has been exhausted" in response_text
                    ):
                        self.log(
                            f"Rate limit hit. Waiting {retry_delay}s before retry ({attempt+1}/{max_retries})..."
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        success = True
                        break  # Success or other error

                duration = round(time.time() - start_time, 2)

                self.log(
                    f"--- [Q{q.number}] Response ({duration}s) ---\n{response_text}\n-----------------------"
                )

                # Update DB
                if success:
                    q.textbook_chat = response_text
                    q.save()

                # Add to Excel Data (Cumulative)
                results_data.append(
                    {
                        "Exam": round_num,
                        "Subject": q.subject.name,
                        "Number": q.number,
                        "Prompt": prompt,
                        "Answer": q.answer,
                        "Textbook Explanation": response_text,
                        "Success": "Success" if success else "Failed",
                        "Time": current_time,
                        "Response Duration (s)": duration,
                    }
                )

                # Incremental Save
                try:
                    df = pd.DataFrame(results_data)
                    df.to_excel(filename, index=False)
                except Exception as save_err:
                    self.log(f"Error saving Excel (i={i}): {save_err}")

                # Update Progress
                progress = ((i + 1) / total) * 100
                self.progress_var.set(progress)
                self.status_lbl.config(text=f"Processed {i+1}/{total}")
                self.root.update_idletasks()

                # Polite delay
                # Polite delay
                time.sleep(2)

            self.log(f"Generation Completed. Results saved to {filename}")

            self.log("Generation Completed.")

        except Exception as e:
            self.log(f"Error during process: {e}")
        finally:
            self.is_running = False
            self.root.after(0, self.reset_buttons)

    def reset_buttons(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = TextbookGeneratorApp(root)
    root.mainloop()
