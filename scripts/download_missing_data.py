import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_engine.loader import DataLoader
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

def main():
    logger.info("Starting missing data download script...")
    
    loader = DataLoader(data_dir="data/raw")
    
    # 获取当前日期作为结束日期
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Target end date: {end_date}")
    
    # 执行全量同步（会自动登录/注销）
    loader.sync_all(end_date=end_date)
    
    logger.info("Download script finished.")

if __name__ == "__main__":
    main()
