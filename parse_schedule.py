import pandas as pd
import sys

# Set display options to show more
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1000)

try:
    df = pd.read_excel("课表.xls", engine="xlrd")
    
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    
    # Print first few rows but only first few columns if there are many
    print("First 5 rows (first 10 cols):")
    print(df.iloc[:5, :10].to_string())
    
except Exception as e:
    print(f"Error: {e}")
