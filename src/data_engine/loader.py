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
        """Fetch Full Market A-share stocks (Point-in-Time)"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        logger.info(f"Fetching FULL MARKET stock list on {date}...")
        
        target_codes = set()
        rs = bs.query_all_stock(date)
        
        if rs.error_code != '0':
            logger.error(f"query_all_stock failed: {rs.error_msg}")
            return []
            
        while rs.next():
            row = rs.get_row_data()
            code = row[0]
            # 过滤 A 股主板、创业板、科创板，剔除 B 股、北交所和指数代码
            if code.startswith('sh.6') or code.startswith('sz.0') or code.startswith('sz.3'):
                target_codes.add(code)
                
        final_list = sorted(list(target_codes))
        logger.info(f"Total target stocks (Full Market): {len(final_list)}")
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

    def incremental_update(self, codes, end_date=None):
        """
        增量更新：只下载每只股票上次数据截止日之后的新数据，并追加合并。
        这样不需要重新下载全量历史，每次只补充最新行情即可。
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Starting INCREMENTAL data update for {len(codes)} stocks up to {end_date}")
        update_count = 0
        skip_count = 0

        for i, code in enumerate(codes):
            file_path = self.data_dir / f"{code}.parquet"
            try:
                if file_path.exists():
                    existing = pd.read_parquet(file_path)
                    existing['date'] = pd.to_datetime(existing['date'])
                    last_date = existing['date'].max()
                    start_date = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    existing = None
                    start_date = "2020-01-01"

                if start_date >= end_date:
                    skip_count += 1
                    continue

                time.sleep(0.5)  # 温和请求，防止被封
                new_df = self.fetch_daily_data(code, start_date, end_date)

                if new_df is not None and not new_df.empty:
                    new_df['date'] = pd.to_datetime(new_df['date'])
                    if existing is not None:
                        merged = pd.concat([existing, new_df], ignore_index=True)
                        merged = merged.drop_duplicates(subset=['date', 'code']).sort_values('date')
                    else:
                        merged = new_df.sort_values('date')
                    merged.to_parquet(file_path, index=False)
                    update_count += 1
                    logger.info(f"[{i+1}/{len(codes)}] {code}: +{len(new_df)} rows ({start_date} ~ {end_date})")
                else:
                    skip_count += 1

            except Exception as e:
                logger.warning(f"Failed to update {code}: {e}")

        logger.info(f"Incremental update done. Updated: {update_count}, Skipped/Up-to-date: {skip_count}")



    def sync_all(self, end_date=None):
        """
        全量同步方案：获取所有指数成分股，并执行增量更新。
        """
        if not self.login():
            return
        
        try:
            codes = self.get_stock_list()
            if codes:
                self.incremental_update(codes, end_date=end_date)
            else:
                logger.error("Could not fetch stock list.")
        finally:
            self.logout()

    def detect_gaps(self, codes, target_start="2020-01-01"):
        """
        检测缺失情况（用于诊断）
        """
        missing_entirely = []
        truncated = []
        
        for code in codes:
            file_path = self.data_dir / f"{code}.parquet"
            if not file_path.exists():
                missing_entirely.append(code)
                continue
            
            try:
                df = pd.read_parquet(file_path)
                if df.empty:
                    missing_entirely.append(code)
                    continue
                
                last_date = pd.to_datetime(df['date']).max().strftime("%Y-%m-%d")
                truncated.append((code, last_date))
            except Exception:
                missing_entirely.append(code)
                
        return missing_entirely, truncated


if __name__ == "__main__":
    # Test script: full sync
    loader = DataLoader()
    loader.sync_all()
