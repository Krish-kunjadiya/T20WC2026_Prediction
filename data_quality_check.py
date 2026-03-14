import pandas as pd
import os
import glob

def check_data_quality():
    data_dir = "Data"
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    findings = []
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            filename = os.path.basename(file)
            findings.append(f"\n--- Analysis for {filename} (Rows: {len(df)}, Cols: {len(df.columns)}) ---")
            
            # 1. Missing/Null data
            null_counts = df.isnull().sum()
            missing_cols = null_counts[null_counts > 0]
            if not missing_cols.empty:
                findings.append("Missing/Null values found:")
                for col, count in missing_cols.items():
                    findings.append(f"  - {col}: {count} missing ({(count/len(df))*100:.2f}%)")
            else:
                findings.append("No missing/null values found.")
                
            # 2. Improper Data Heuristics (Empty strings, weird values)
            # Checking string columns for purely empty or just whitespace
            str_cols = df.select_dtypes(include=['object']).columns
            for col in str_cols:
                empty_str_count = df[col].astype(str).str.strip().eq('').sum()
                if empty_str_count > 0:
                    findings.append(f"  - {col} has {empty_str_count} empty strings.")
            
            # Checking numeric columns for negative values where they might not make sense
            num_cols = df.select_dtypes(include=['int64', 'float64']).columns
            for col in num_cols:
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    findings.append(f"  - {col} has {negative_count} negative values.")
                    
        except Exception as e:
            findings.append(f"\nCould not analyze {file}: {e}")
            
    print("\n".join(findings))

if __name__ == "__main__":
    check_data_quality()
