import sys
try:
    import pandas as pd
except ImportError:
    print("pandas not installed")
    sys.exit(1)

file_path = "2026년예정_도장및방수공사수요_260310.xlsx"
try:
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    print(df.head(5).to_markdown())
except Exception as e:
    print(f"Error reading excel: {e}")
