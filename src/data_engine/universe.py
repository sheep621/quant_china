import pandas as pd
import yaml
from pathlib import Path
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class UniverseFilter:
    def __init__(self, config_path="config/universe.yaml"):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load universe config, using default: {e}")
            return {"common": {"exclude_st": True, "exclude_halt": True}}
            
    def filter(self, daily_df, stock_basic_info=None):
        """
        Filter stocks based on daily metrics and static info
        daily_df: DataFrame with multiple stocks for ONE day (Cross-section)
        or time-series for pre-filtering?
        
        Usually Universe selection happens daily. 
        """
        if daily_df is None or daily_df.empty:
            return daily_df
            
        common_cfg = self.config.get('common', {})
        
        # 1. Exclude ST
        if common_cfg.get('exclude_st', True) and 'isST' in daily_df.columns:
            # BaoStock isST: 1=ST, 0=Normal
            daily_df = daily_df[daily_df['isST'] == '0']
            
        # 2. Exclude Halt (processed in Cleaner usually, but double check)
        if common_cfg.get('exclude_halt', True) and 'tradestatus' in daily_df.columns:
            daily_df = daily_df[daily_df['tradestatus'] == '1']
            
        # 3. Liquidity Filter (if 'amount' exists)
        liq_cfg = self.config.get('liquidity', {})
        min_amt = liq_cfg.get('min_amount_ma20', 0)
        if min_amt > 0 and 'amount' in daily_df.columns:
            # Note: Single day amount is not MA20. Real system needs rolling calc.
            # Here for simplicity we filter extremely low liquidity on the day
            daily_df = daily_df[daily_df['amount'] > (min_amt / 5)] # Loose filter
            
        return daily_df
