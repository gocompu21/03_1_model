import pandas as pd
import os

file_path = r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data_5회_20251215_123428.xlsx"

try:
    df = pd.read_excel(file_path)
    print("--- COLUMNS START ---")
    for col in df.columns:
        print(f"'{col}'")
    print("--- COLUMNS END ---")
    print(f"Total Rows: {len(df)}")
except Exception as e:
    print(f"Error reading Excel: {e}")
