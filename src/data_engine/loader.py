import baostock as bs
import pandas as pd
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class DataLoader:
    def __init__(self, data_dir="data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def login(self):
        lg = bs.login()
        if lg.error_code != '0':
            logger.error(f"BaoStock login failed: {lg.error_msg}")
            return False
        logger.info("BaoStock login success")
        return True

    def logout(self):
        bs.logout()
        logger.info("BaoStock logout")

    def get_stock_list(self, date=None):
        """Fetch liquid A-share stocks (HS300 + ZZ500 + SZ50)"""
        if date is None:
            # Use a recent trading date to ensure we get constituents
            date = datetime.now().strftime("%Y-%m-%d")
            
        logger.info(f"Fetching stock list from Major Indices (HS300, ZZ500, SZ50) on {date}...")
        
        target_codes = set()
        
        # Helper to query and add
        def _add_index(rs_func, name):
            rs = rs_func(date)
            if rs.error_code != '0':
                logger.warning(f"{name} query failed: {rs.error_msg}")
                return
            while rs.next():
                # code is usually at index 1: update_date, code, code_name
                target_codes.add(rs.get_row_data()[1])
        
        _add_index(bs.query_hs300_stocks, "HS300")
        _add_index(bs.query_zz500_stocks, "ZZ500")
        _add_index(bs.query_sz50_stocks, "SZ50")
            
        # Fallback to recent known date if empty (e.g. today is holiday)
        if len(target_codes) < 100:
            logger.warning("Few stocks found (Holiday?). Trying fallback date 2023-12-01...")
            fallback_date = "2023-12-01"
            
            def _add_index_fb(rs_func):
                rs = rs_func(fallback_date)
                while (rs.error_code == '0') & rs.next():
                     target_codes.add(rs.get_row_data()[1])
            
            _add_index_fb(bs.query_hs300_stocks)
            _add_index_fb(bs.query_zz500_stocks)
            _add_index_fb(bs.query_sz50_stocks)
        
        final_list = sorted(list(target_codes))
        logger.info(f"Total target stocks (Index Constituents): {len(final_list)}")
        return final_list

    def fetch_daily_data(self, code, start_date, end_date):
        """
        Fetch daily K-line data
        adjustflag: 3=No Adjust, 2=Forward Adjust, 1=Back Adjust
        We use 2 (Forward Adjust) for easier backtesting signal calculation
        """
        # Fields: date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST
        fields = "date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
        
        rs = bs.query_history_k_data_plus(code,
            fields,
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="2")
            
        if rs.error_code != '0':
            logger.warning(f"query_history_k_data_plus failed for {code}: {rs.error_msg}")
            return None
            
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
            
        if not data_list:
            return None
            
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn', 'pctChg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df

    def update_data(self, codes, start_date, end_date):
        """Update data for a list of codes"""
        logger.info(f"Starting data update for {len(codes)} stocks from {start_date} to {end_date}")
        
        success_count = 0
        skipped_count = 0
        
        for i, code in enumerate(codes):
            file_path = self.data_dir / f"{code}.parquet"
            
            # Resume capability: Check if file exists and is valid
            if file_path.exists():
                try:
                    # Simple check: if file size > 1KB, assume it's valid enough for resume
                    # Loading parquet to check date is safer but slower. 
                    # Let's check size first.
                    if file_path.stat().st_size > 1000:
                         # Optional: Read meta to check end_date?
                         # For now/speed: Just assume if file exists, it's done. 
                         # User can delete data/raw to force partial re-download.
                         skipped_count += 1
                         if i % 100 == 0:
                            logger.info(f"Checking {i}/{len(codes)} stocks (Skipped {skipped_count})...")
                         continue
                except Exception:
                    pass
            
            current_start = start_date
            
            try:
                # Fetch
                df = self.fetch_daily_data(code, current_start, end_date)
                if df is not None and not df.empty:
                    df.to_parquet(file_path, index=False)
                    success_count += 1
            except Exception as e:
                logger.error(f"Error updating {code}: {e}")
            
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(codes)} stocks (Success: {success_count}, Skipped: {skipped_count})...")
                
        logger.info(f"Data update completed. Success: {success_count}, Skipped: {skipped_count}, Total: {len(codes)}")

if __name__ == "__main__":
    # Test script
    loader = DataLoader()
    if loader.login():
        # Test with one stock: Ping An Bank
        test_code = "sz.000001"
        logger.info(f"Fetching {test_code}...")
        df = loader.fetch_daily_data(test_code, "2023-01-01", "2023-12-31")
        if df is not None:
            logger.info(f"Fetched {len(df)} rows. Head:\n{df.head()}")
            
            # Save test
            loader.update_data([test_code], "2023-01-01", "2023-12-31")
        else:
            logger.error("Fetch failed")
            
        loader.logout()
