import os
import time
import json
import logging
import google.generativeai as genai
from datetime import datetime

STORES_FILE = "local_stores.json"

SYSTEM_INSTRUCTION = (
    "당신은 나무의사 자격 시험을 준비하는 수험생을 위한 튜터입니다. "
    "제공된 지식 저장소 파일(기본서, 법령 등)의 내용을 바탕으로 사용자의 질문에 정확하고 간결하게 답변하세요. "
    "1. 질문과 관련 없는 내용은 포함하지 마십시오. "
    "2. 책의 목차나 서지 정보를 무의미하게 나열하지 마십시오. "
    "3. 책의 이름을 알려주지 마십시오. "
    "4. 답변은 핵심 내용을 중심으로 서술형으로 작성하되, 필요하다면 가독성을 위해 글머리 기호를 사용하세요. "
    "5. 제공된 파일에 정답이 명확히 없다면, '제공된 자료에서 관련 내용을 찾을 수 없습니다.'라고 솔직하게 말하세요."
    "6. 질문이 객관식 문제일 경우에는 정답을 먼저 제시한 다음, 선지별로 답변을 제시하세요. 마지막 정답에 대한 설명으로 정리하세요"
    "7. 화학식(예: 이산화탄소)이나 수식은 반드시 LaTeX 문법(예: $\\text{CO}_2$)을 사용하여 작성하세요. "
    "   특히, 모든 LaTeX 수식 앞뒤에는 반드시 $ 기호를 붙여야 합니다 (예: $\\text{SO}_2$, $x^2$). "
)


class GeminiStoreManager:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            self.configure_genai(api_key)
        self.stores = self.load_local_stores()

    def configure_genai(self, key):
        # Sanitize
        if key.startswith("@"):
            key = key[1:]
        self.api_key = key.strip()
        genai.configure(api_key=self.api_key)

    def set_api_key(self, key):
        self.configure_genai(key)

    def load_local_stores(self):
        if os.path.exists(STORES_FILE):
            try:
                with open(STORES_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_local_stores(self):
        with open(STORES_FILE, "w") as f:
            json.dump(self.stores, f, indent=4)

    def list_stores(self):
        """Returns a list of virtual stores."""
        return [
            {"name": name, "display_name": name, "file_count": len(files)}
            for name, files in self.stores.items()
        ]

    def list_all_files(self):
        """Lists all files in the cloud (for reference)."""
        if not self.api_key:
            return []
        files = []
        try:
            for f in genai.list_files():
                files.append(
                    {
                        "name": f.name,
                        "display_name": f.display_name,
                        "state": f.state.name,
                    }
                )
        except:
            pass  # Ignore if API fails
        return files

    def sync_all_stores(self):
        """Proactively syncs all valid cloud files to local stores."""
        if not self.api_key:
            return

        try:
            cloud_files = self.list_all_files()
            new_stores = {}
            import unicodedata

            # Predefined subjects or inferred loop?
            # Better to infer from file names or strict subject list?
            # Let's infer but strictly.

            # Common Subjects
            # Subject Mapping (Store Name -> List of Keywords)
            subject_mappings = {
                "수목생리학": ["수목생리학"],
                "수목병리학": ["수목병리학"],
                "수목해충학": ["수목해충학"],
                "산림토양학": ["산림토양학", "토양학"],
                "수목관리학": ["수목관리학", "조경수", "식재관리"],
            }

            for subject, keywords in subject_mappings.items():
                new_stores[subject] = []

                for f in cloud_files:
                    if f["state"] == "ACTIVE":
                        norm_name = unicodedata.normalize("NFC", f["display_name"])
                        # Check if ANY keyword matches
                        if any(k in norm_name for k in keywords):
                            new_stores[subject].append(f["name"])

            # Apply update
            self.stores = new_stores
            self.save_local_stores()
            logging.info(f"Synced stores: {self.stores}")
            return self.stores
        except Exception as e:
            logging.error(f"Sync failed: {e}")
            return {}

    def create_store_with_files(self, store_name, file_paths, progress_callback=None):
        if not self.api_key:
            raise ValueError("API Key not set.")

        # upload files
        uploaded_names = []
        total = len(file_paths)

        for i, path in enumerate(file_paths):
            if progress_callback:
                progress_callback(f"Uploading {i+1}/{total}: {os.path.basename(path)}")
            try:
                f = genai.upload_file(path=path)
                uploaded_names.append(f.name)
            except Exception as e:
                print(f"Failed {path}: {e}")

        if progress_callback:
            progress_callback("Waiting for processing...")

        # Wait
        valid_files = []
        for name in uploaded_names:
            while True:
                f = genai.get_file(name)
                if f.state.name == "PROCESSING":
                    time.sleep(1)
                else:
                    if f.state.name == "ACTIVE":
                        valid_files.append(name)
                    break

        # Save to local store
        if store_name not in self.stores:
            self.stores[store_name] = []

        self.stores[store_name].extend(valid_files)
        self.save_local_stores()

        if progress_callback:
            progress_callback("Store updated.")

    def delete_store(self, store_name):
        if store_name in self.stores:
            del self.stores[store_name]
            self.save_local_stores()

    def delete_file(self, file_name):
        if not self.api_key:
            raise ValueError("API Key not set.")
        try:
            genai.delete_file(file_name)
            # Also remove from local stores if present
            for store in self.stores:
                if file_name in self.stores[store]:
                    self.stores[store].remove(file_name)
            self.save_local_stores()
        except Exception as e:
            logging.error(f"Error deleting file {file_name}: {e}")
            raise e

    def query_store(self, store_name, query_text):
        if not self.api_key:
            return "API Key not set."

        if store_name not in self.stores:
            return "Store not found."

        file_names = self.stores[store_name]
        if not file_names:
            return "Store is empty."

        try:
            # Fetch file objects and filter for validity
            files = []
            files_to_remove = []
            valid_states = ["ACTIVE"]
            for name in file_names:
                try:
                    f = genai.get_file(name)
                    if f.state.name in valid_states:
                        files.append(f)
                    else:
                        logging.warning(f"Skipping file {name} (State: {f.state.name})")
                except Exception as e:
                    # If 403 or 404, the file is likely gone or inaccessible.
                    # We should remove it from our local store to prevent future warnings.
                    logging.warning(
                        f"Could not retrieve file {name}: {e}. Marking for removal."
                    )
                    files_to_remove.append(name)

            if files_to_remove:
                for name in files_to_remove:
                    if name in self.stores[store_name]:
                        self.stores[store_name].remove(name)
                self.save_local_stores()

            if not files:
                return "No valid (ACTIVE) files found in this store."

            model = genai.GenerativeModel(
                "gemini-2.5-flash", system_instruction=SYSTEM_INSTRUCTION
            )

            # Explicitly structure the content parts for clarity
            # Some model versions are strict about list structure [File, ..., Text]
            content_parts = list(files)
            content_parts.append(query_text)

            # Disable safety settings to prevent false positives on quiz content
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ]

            # Configure generation options
            generation_config = genai.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7,
            )

            response = model.generate_content(
                content_parts,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
            return response.text
        except Exception as e:
            logging.error(f"Query Error: {e}")
            return f"Error querying: {e}"
