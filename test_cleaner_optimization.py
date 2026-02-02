
import pandas as pd
import numpy as np
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.data_engine.cleaner import DataCleaner

def test_cleaner_logic():
    print("=== Testing DataCleaner Optimizations ===")
    cleaner = DataCleaner()
    
    # 1. Test MAD Outlier Detection
    print("\n[Test 1] MAD Outlier Detection")
    # Generate data: 100 normal points (mean=10) + 1 extreme outlier (1000)
    np.random.seed(42)
    normal_data = np.random.normal(10, 1, 100)
    data = np.append(normal_data, [1000]) # 1000 is huge outlier
    
    df_mad = pd.DataFrame({'volume': data, 'amount': data, 'turn': data})
    
    # Process (only mad check part)
    # We need to mock other columns to pass process_daily_data
    df_mad['date'] = '2023-01-01'
    df_mad['code'] = 'sh.600000'
    
    # We can just call mad_clean directly to test logic
    cleaned_series = cleaner.mad_clean(pd.Series(data), n=5.0)
    max_val = cleaned_series.max()
    print(f"Original Max: {data.max()}")
    print(f"Cleaned Max (MAD n=5): {max_val}")
    
    if max_val < 100:
        print("PASS: Outlier clipped successfully.")
    else:
        print(f"FAIL: Outlier {max_val} still looks too high (expected < ~20).")

    # 2. Test Limit Up/Down Logic
    print("\n[Test 2] Limit Detection (Main Board vs STAR/ChiNext vs ST)")
    
    test_cases = [
        # Code, PctChg, IsST, Expected_LimitUp
        ('sh.600000', 9.9, '0', True),   # Main Board > 9.8% -> UP
        ('sh.600000', 5.0, '0', False),  # Main Board < 9.8% -> Normal
        
        ('sh.688001', 12.0, '0', False), # STAR Market 12% -> Normal (Limit is 20%)
        ('sh.688001', 19.9, '0', True),  # STAR Market > 19.8% -> UP
        
        ('sz.300001', 11.0, '0', False), # ChiNext 11% -> Normal
        ('sz.300001', 20.0, '0', True),  # ChiNext 20% -> UP
        
        ('sh.600000', 5.0, '1', True),   # ST Stock (Main) > 4.8% -> UP
        ('sz.300001', 5.0, '1', True),   # ST Stock (ChiNext) -> Treat as 5% per our simplified rule? 
                                         # (Real rule complex, but we defined ST=1 as 5% priority)
    ]
    
    rows = []
    for code, chg, st, exp in test_cases:
        rows.append({
            'date': '2023-01-01',
            'code': code, 
            'pctChg': chg,
            'isST': st,
            'tradeStatus': '1',
            'open': 10, 'close': 10, 'high': 10, 'low': 10, 'volume': 100, 'amount': 1000, 'turn': 1
        })
        
    df_limit = pd.DataFrame(rows)
    # Adding next_open for label generation to avoid error
    df_limit['next_open'] = 10
    
    processed_df = cleaner.process_daily_data(df_limit)
    
    print(f"{'Code':<10} {'Pct':<5} {'ST':<3} {'Exp':<5} {'Act':<5} {'Result'}")
    all_pass = True
    for i, row in processed_df.iterrows():
        exp = test_cases[i][3]
        act = row['is_limit_up']
        res = "PASS" if exp == act else "FAIL"
        if res == "FAIL": all_pass = False
        print(f"{row['code']:<10} {row['pctChg']:<5} {row['isST']:<3} {str(exp):<5} {str(bool(act)):<5} {res}")
        
    if all_pass:
        print("\nPASS: All Limit Detection logic verified.")
    else:
        print("\nFAIL: Some Limit Detection logic failed.")

if __name__ == "__main__":
    test_cleaner_logic()
