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
    
    def mad_clean(self, series, n=3.0, constant=1.4826):
        """
        MAD (Median Absolute Deviation) 去极值
        Robust Check: median +/- n * mad * constant
        Constant 1.4826 makes MAD consistent with Std Dev for normal distribution.
        """
        median = series.median()
        mad = (series - median).abs().median()
        
        # Avoid zero MAD causing infinite thresholds (common in low liquidity)
        if mad == 0:
            return series
            
        threshold = n * mad * constant
        lower_bound = median - threshold
        upper_bound = median + threshold
        
        return series.clip(lower=lower_bound, upper=upper_bound)
        
    def process_daily_data(self, df):
        """
        清洗并特征工程 - 优化版
        
        新增处理:
        1. Rank归一化量价特征
        2. MAD去极值 (替代Winsorize)
        3. 改进的涨跌停检测 (支持科创板/创业板 20%)
        4. 计算 High Limit (涨停价) 用于 limit_distance 算子
        5. 修正: 使用 groupby 进行 shift 操作, 防止不同股票数据由于排序混杂
        """
        if df is None or df.empty:
            return None
            
        # 必须确保有 code 列
        if 'code' not in df.columns:
            logger.warning("Data missing 'code' column, treating as single stock")
            df['code'] = 'mock_code'
        
        # Sort by code and date to ensure correct grouping structure (optional but safe)
        if 'date' in df.columns:
            df = df.sort_values(['code', 'date']).reset_index(drop=True)

        # 1. Filter Suspended Stocks
        if 'tradestatus' in df.columns:
            df = df[df['tradestatus'] == '1'].copy()
            
        # 2. Limit Logic & Limit Price Calculation
        # 需要计算 high_limit 供 limit_distance 算子使用
        # 逻辑: High_Limit = PreClose * (1 + Limit_Ratio)
        
        # 获取 PreClose (如果不存在则推导)
        if 'preClose' not in df.columns:
            df['preClose'] = df.groupby('code')['close'].shift(1)
            
        if 'pctChg' in df.columns:
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')

        # Limit Ratio Determination
        # 默认 10%
        df['limit_ratio'] = 0.10
        
        # 科创板(sh.688) / 创业板(sz.300) -> 20%
        is_20pct = df['code'].str.startswith(('sh.688', 'sz.300'))
        df.loc[is_20pct, 'limit_ratio'] = 0.20
        
        # ST -> 5% (简化逻辑: isST==1 则 5%)
        # 注意: 创业板ST也是20%, 但为保守起见, 若标记为ST则统一限制严格
        if 'isST' in df.columns:
            # isST可能是字符串'1'或数字1
            is_st = (df['isST'].astype(str) == '1')
            df.loc[is_st, 'limit_ratio'] = 0.05
            
        # 计算 High Limit (A股规则: 四舍五入到分)
        # 价格通常是浮点数, A股最小跳动 0.01
        # 公式: round(preClose * (1+ratio) * 100) / 100
        if 'preClose' in df.columns:
            # 向量化计算
            limit_price = df['preClose'] * (1 + df['limit_ratio'])
            # 模拟交易所四舍五入逻辑 (这里简单用 round(2) )
            df['high_limit'] = limit_price.round(2)
        else:
            # 无法计算, 填为 -1 或 NaN
            df['high_limit'] = np.nan

        # Limit Up/Down Flag
        if 'high_limit' in df.columns and 'close' in df.columns:
            # 宽松判定: 收盘价 >= 涨停价 - 0.01 (考虑到精度)
            df['is_limit_up'] = df['close'] >= (df['high_limit'] - 0.01)
            
            # 跌停价计算类似: PreClose * (1 - Limit_Ratio)
            low_limit = df['preClose'] * (1 - df['limit_ratio'])
            low_limit = low_limit.round(2)
            df['is_limit_down'] = df['close'] <= (low_limit + 0.01)
        
        # 3. 特征预处理 (Rank + MAD)
        cols_to_process = [c for c in ['volume', 'amount', 'turn', 'pctChg'] if c in df.columns]
        
        if 'date' in df.columns:
            for col in cols_to_process:
                # 1. Cross-sectional MAD
                daily_medians = df.groupby('date')[col].transform('median')
                daily_dev = (df[col] - daily_medians).abs()
                daily_mad = daily_dev.groupby(df['date']).transform('median')
                
                # Threshold: n=5 * 1.4826 ~ 7.4 sigma
                threshold = 5.0 * daily_mad * 1.4826
                lower = daily_medians - threshold
                upper = daily_medians + threshold
                
                winsorized = df[col].clip(lower, upper)
                df[f'{col}_winsorized'] = winsorized
                
                # 2. Cross-sectional Rank
                # 使用 transform 进行组内 Rank
                # 注意: pandas rank可能较慢, 但正确性优先
                df[f'{col}_rank'] = df.groupby('date')[f'{col}_winsorized'].transform(lambda x: x.rank(pct=True))

        # 4. Generate Label (T+1 Strategy)
        # CRITICAL FIX: Group by code for shifts!
        # Label: (Open_T+2 / Open_T+1) - 1
        # 需要 shift(-1) 得到 T+1 Open, shift(-2) 得到 T+2 Open
        
        grouped_open = df.groupby('code')['open']
        df['next_open'] = grouped_open.shift(-1)   # Open_T+1
        df['next_2_open'] = grouped_open.shift(-2) # Open_T+2
        
        # 计算收益率
        df['label'] = (df['next_2_open'] / df['next_open']) - 1.0
        
        return df

    def filter_universe(self, df):
        """Additional filtering if needed"""
        return df
