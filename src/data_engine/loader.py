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
        """Fetch Full Market A-share stocks (Point-in-Time) with weekend fallback"""
        from datetime import datetime, timedelta
        
        if date is None:
            query_date = datetime.now()
        else:
            query_date = datetime.strptime(date, "%Y-%m-%d")
            
        # 自动往前推最多 7 天，确保一定能碰上一个交易日
        for _ in range(7):
            date_str = query_date.strftime("%Y-%m-%d")
            logger.info(f"Fetching FULL MARKET stock list on {date_str}...")
            
            target_codes = set()
            rs = bs.query_all_stock(date_str)
            
            if rs.error_code == '0':
                while rs.next():
                    row = rs.get_row_data()
                    code = row[0]
                    # 过滤 A 股主板、创业板、科创板，剔除 B 股、北交所和指数代码
                    if code.startswith('sh.6') or code.startswith('sz.0') or code.startswith('sz.3'):
                        target_codes.add(code)
            
            # 如果成功获取到了股票（大于0），说明碰到了交易日
            if len(target_codes) > 0:
                final_list = sorted(list(target_codes))
                logger.info(f"Total target stocks (Full Market): {len(final_list)} (Found on {date_str})")
                return final_list, date_str # 返回列表和查找到的真实交易日
                
            # 如果没获取到（比如是周末或节假日），往前推一天继续试
            logger.warning(f"{date_str} returned 0 stocks (likely a weekend/holiday). Stepping back 1 day...")
            query_date -= timedelta(days=1)
            
        logger.error("Could not fetch stock list after checking the past 7 days.")
        return [], None

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

    def fetch_benchmark_data(self, code="sh.000300", start_date="2020-01-01", end_date="2024-01-01"):
        """
        专用查询接口：拉取指数历史日线（不复权、无换手率、无ST标记）
        """
        fields = "date,code,open,high,low,close,volume,amount,pctChg"
        
        max_retries = 3
        for attempt in range(max_retries):
            # 指数通常使用 adjustflag="3" (不复权)
            rs = bs.query_history_k_data_plus(code,
                fields,
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="3")
                
            if rs.error_code == '0':
                break
                
            logger.warning(f"Benchmark attempt {attempt+1}/{max_retries} failed for {code}: {rs.error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                
        if rs.error_code != '0':
            logger.error(f"Failed to fetch benchmark {code}: {rs.error_msg}")
            return None
            
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
            
        if not data_list:
            return None
            
        df = pd.DataFrame(data_list, columns=rs.fields)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pctChg']
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
        增量更新：并行版本。
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Starting PARALLEL INCREMENTAL update for {len(codes)} stocks up to {end_date}")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        lock = threading.Lock()
        stats = {"update_count": 0, "skip_count": 0}

        def _worker(code):
            file_path = self.data_dir / f"{code}.parquet"
            try:
                if file_path.exists():
                    # 预检日期：如果本地最新日期已达到目标日期，则标记为 Skip
                    # 这里直接读 parquet 最后一行的快照
                    existing = pd.read_parquet(file_path)
                    if existing.empty:
                        last_date_str = "2020-01-01"
                        existing = None
                    else:
                        existing['date'] = pd.to_datetime(existing['date'])
                        last_date_str = existing['date'].max().strftime("%Y-%m-%d")
                    
                    start_today = (pd.to_datetime(last_date_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                    
                    if last_date_str >= end_date:
                        with lock: stats["skip_count"] += 1
                        return
                else:
                    existing = None
                    start_today = "2020-01-01"

                # 确实需要下载时，拉长间隔至 1.5s
                time.sleep(1.5) 
                new_df = self.fetch_daily_data(code, start_today, end_date)

                if new_df is not None and not new_df.empty:
                    new_df['date'] = pd.to_datetime(new_df['date'])
                    if existing is not None:
                        merged = pd.concat([existing, new_df], ignore_index=True)
                        merged = merged.drop_duplicates(subset=['date', 'code']).sort_values('date')
                    else:
                        merged = new_df.sort_values('date')
                    merged.to_parquet(file_path, index=False)
                    with lock: stats["update_count"] += 1
                else:
                    with lock: stats["skip_count"] += 1

            except Exception as e:
                logger.warning(f"Worker failed for {code}: {e}")

        # 鉴于 Baostock 对并发及 IP 频率极其敏感，且 5500 只标的数量巨大：
        # 这里切换回“稳定模式”：单线程 + 更长的 sleep
        logger.info(f"Using STABLE SERIAL mode to ensure data integrity...")
        
        success_count = stats["update_count"]
        skip_count = stats["skip_count"]
        
        for i, code in enumerate(codes):
            _worker(code)
            if (i + 1) % 20 == 0 or (i + 1) == len(codes):
                logger.info(f"Sync Progress: {i+1}/{len(codes)} (Updated: {stats['update_count']}, Skipped: {stats['skip_count']})")

        logger.info(f"Incremental update done. Updated: {stats['update_count']}, Skipped: {stats['skip_count']}")

    def sync_all(self, end_date=None):
        """
        全量同步方案：获取最新交易日作为锚点。
        """
        if not self.login():
            return
        
        try:
            # 1. 探测最新可用交易日
            codes, last_market_date = self.get_stock_list()
            
            if not codes or not last_market_date:
                logger.error("Could not fetch valid stock list or market date.")
                return

            # 如果用户没传 end_date，强制使用探测到的交易日，防止周末空转
            target_end_date = end_date or last_market_date
            
            logger.info(f"Target Sync Point: {target_end_date}")
            self.incremental_update(codes, end_date=target_end_date)
            
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
