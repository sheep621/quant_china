import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class DataCleaner:
    def __init__(self, config=None):
        self.config = config or {}
        
    def rank_normalize(self, series):
        """
        Rank归一化 - WQ101核心预处理
        将数值映射到[0,1]区间,去除极值影响
        """
        return series.rank(pct=True)
    
    def winsorize(self, series, lower=0.01, upper=0.99):
        """
        Winsorize去极值
        将异常值截断到1%和99%分位
        """
        lower_bound = series.quantile(lower)
        upper_bound = series.quantile(upper)
        return series.clip(lower=lower_bound, upper=upper_bound)
        
    def process_daily_data(self, df):
        """
        清洗并特征工程 - 优化版
        
        新增处理:
        1. Rank归一化量价特征
        2. Winsorize去极值
        3. 改进的涨跌停检测
        """
        if df is None or df.empty:
            return None
            
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # 1. Filter Suspended Stocks
        if 'tradestatus' in df.columns:
            df = df[df['tradestatus'] == '1'].copy()
            
        # 2. Limit Detection (优化)
        # 使用更准确的pctChg阈值判断
        df['is_limit_up'] = df['pctChg'] >= 9.8  # 主板/中小创
        df['is_limit_down'] = df['pctChg'] <= -9.8
        
        # ST股票单独处理 (5%)
        if 'isST' in df.columns:
            st_mask = (df['isST'] == '1')
            df.loc[st_mask, 'is_limit_up'] = df.loc[st_mask, 'pctChg'] >= 4.8
            df.loc[st_mask, 'is_limit_down'] = df.loc[st_mask, 'pctChg'] <= -4.8
        
        # 3. 特征预处理 (Rank + Winsorize)
        for col in ['volume', 'amount', 'turn']:
            if col in df.columns:
                # Step 1: Winsorize去极值
                df[f'{col}_winsorized'] = self.winsorize(df[col])
                
                # Step 2: Rank归一化
                df[f'{col}_rank'] = self.rank_normalize(df[f'{col}_winsorized'])
        
        # 对价格变化也做Rank
        if 'pctChg' in df.columns:
            df['pctChg_rank'] = self.rank_normalize(df['pctChg'])
        
        # 4. Generate Label (T+1 Strategy)
        df['next_open'] = df['open'].shift(-1)
        df['next_2_open'] = df['open'].shift(-2)
        df['label'] = df['next_2_open'] / df['next_open'] - 1.0
        
        return df

    def filter_universe(self, df):
        """Additional filtering if needed"""
        return df
