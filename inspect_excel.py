import pandas as pd
import os

file_path = r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data\전체데이터_5회_11회_전체해설_인포그래픽추가본.xlsx"

try:
    df = pd.read_excel(file_path, nrows=1)
    print("Columns found:")
    print(list(df.columns))
except ImportError:
    print("Pandas not installed. Please run: pip install pandas openpyxl")
except Exception as e:
    print(f"Error reading file: {e}")
