import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class DataCleaner:
    def __init__(self, config=None):
        self.config = config or {}
        
    def process_daily_data(self, df):
        """
        Clean and feature engineer a single stock's dataframe
        df columns assumed: date,code,open,high,low,close,volume,amount,adjustflag,turn,tradestatus,pctChg,isST
        """
        if df is None or df.empty:
            return None
            
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # 1. Filter Suspended Stocks (tradestatus=0 is halt in BaoStock? Actually BaoStock tradestatus: 1=trade, 0=halt)
        if 'tradestatus' in df.columns:
            df = df[df['tradestatus'] == '1'].copy()
            
        # 2. Identify Limits
        # Heuristic: pctChg > 9.5% for Main board, > 19.5% for KC/CY. 
        # But st is 4.9%.
        # A safer way is checking if High == Close and pctChg > 0 (Limit Up)
        # Low == Close and pctChg < 0 (Limit Down)
        # Note: This is an approximation.
        
        # Create masks
        # is_limit_up: Buy orders likely fail
        df['is_limit_up'] = (df['close'] == df['high']) & (df['pctChg'] > 4.5) 
        # is_limit_down: Sell orders likely fail
        df['is_limit_down'] = (df['close'] == df['low']) & (df['pctChg'] < -4.5)
        
        # 3. Generate Label for T+1 Strategy
        # We trade at T end or T+1 Open?
        # Standard: Decision at T close, execution at T+1 Open.
        # So we hold from T+1 Open to T+2 Open (1 day).
        # Return = T+2 Open / T+1 Open - 1
        
        # shift(-1) is T+1. shift(-2) is T+2.
        df['next_open'] = df['open'].shift(-1)
        df['next_2_open'] = df['open'].shift(-2)
        
        df['label'] = df['next_2_open'] / df['next_open'] - 1.0
        
        # 4. Filter invalid labels (NaN at the end)
        # We keep the rows but label might be NaN
        
        return df

    def filter_universe(self, df):
        """Additional filtering if needed"""
        return df
