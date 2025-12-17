import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data")

targets = [(8, 55), (10, 34), (10, 35)]


def search_files():
    for round_num, q_num in targets:
        dir_path = BASE_DIR / f"{round_num}회"
        if not dir_path.exists():
            print(f"Directory not found: {dir_path}")
            continue

        print(f"\nSearching in {dir_path} for number {q_num}...")
        found = False
        try:
            for f in os.listdir(dir_path):
                if str(q_num) in f:
                    print(f"  Found candidate: {f}")
                    found = True
        except Exception as e:
            print(f"Error reading dir: {e}")

        if not found:
            print(f"  No file found containing '{q_num}'")


if __name__ == "__main__":
    search_files()
