import pandas as pd

file_path = 'data/수목생리학_용어정리.xlsx'
try:
    df = pd.read_excel(file_path, nrows=5)
    print(df.columns.tolist())
    print(df.head(3))
except Exception as e:
    print(e)
