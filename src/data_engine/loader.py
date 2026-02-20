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
        
        # 添加带指数退避的重试机制，应对[Errno 32] Broken pipe
        max_retries = 3
        for attempt in range(max_retries):
            rs = bs.query_history_k_data_plus(code,
                fields,
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="1")
                
            if rs.error_code == '0':
                break
            
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed for {code}: {rs.error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # 指数退避: 1s, 2s...
        
        if rs.error_code != '0':
            logger.error(f"query_history_k_data_plus finally failed for {code}: {rs.error_msg}")
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
        """Update data for a list of codes (Parallel Version)"""
        logger.info(f"Starting PARALLEL data update for {len(codes)} stocks from {start_date} to {end_date}")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        success_count = 0
        skipped_count = 0
        lock = threading.Lock()
        
        def _process_single_stock(code):
            nonlocal success_count, skipped_count
            
            file_path = self.data_dir / f"{code}.parquet"
            
            # Resume capability
            if file_path.exists():
                try:
                    if file_path.stat().st_size > 1000:
                         with lock:
                             skipped_count += 1
                             if (success_count + skipped_count) % 100 == 0:
                                logger.info(f"Progress: {success_count + skipped_count}/{len(codes)} (Skipped: {skipped_count})")
                         return
                except Exception:
                    pass
            
            try:
                # 针对云环境(GitHub Actions)，拉长间隔防止被Baostock封禁IP或切断数据流
                time.sleep(1.5)
                # Fetch
                df = self.fetch_daily_data(code, start_date, end_date)
                if df is not None and not df.empty:
                    df.to_parquet(file_path, index=False)
                    with lock:
                        success_count += 1
            except Exception as e:
                logger.error(f"Error updating {code}: {e}")
                
            with lock:
                if (success_count + skipped_count) % 100 == 0:
                    logger.info(f"Progress: {success_count + skipped_count}/{len(codes)} (Success: {success_count}, Skipped: {skipped_count})")

        # 修改并发数为1：Baostock对云主机IP的并发限制极严，多线程容易抛出解压失败或Broken Pipe
        max_workers = 1 
        logger.info(f"Using {max_workers} threads to be extremely gentle on Baostock servers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_process_single_stock, code) for code in codes]
            # Wait for all to complete
            for future in as_completed(futures):
                pass
                
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
