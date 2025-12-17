import pandas as pd

FILE_PATH = r"c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model\data\전체데이터_5회_11회_전체해설_인포그래픽추가본.xlsx"

try:
    df = pd.read_excel(FILE_PATH)
    print("Unique Subjects:")
    print(df["과목"].unique())
    print("\nUnique Answers:")
    print(df["정답"].unique())
except Exception as e:
    print(e)
