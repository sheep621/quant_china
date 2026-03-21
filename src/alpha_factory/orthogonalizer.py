import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class Orthogonalizer:
    def __init__(self, method='incremental', threshold=0.7):
        self.method = method
        self.threshold = threshold
        
    def neutralize_size(self, factor_series, X_df, dates_series):
        """
        【Barra 风格中性化】：强制剔除市值(Size)带来的虚假 Beta 敞口。
        量化界常识：如果不用回归剔除市值，你挖出的因子大概率只是微盘股因子的翻版。
        """
        df = pd.DataFrame({
            'factor': factor_series.values,
            'amount': X_df['amount'].values,
            'turn': X_df['turn'].values,
            'date': dates_series.values
        }, index=factor_series.index)
        
        # 1. 代理计算流通市值的对数：log(成交额 / 换手率)
        turn_safe = df['turn'].replace(0, np.nan).fillna(df['turn'].median() + 1e-8)
        df['market_cap'] = df['amount'] / turn_safe
        df['log_size'] = np.log(df['market_cap'] + 1)
        df['log_size'] = df['log_size'].replace([np.inf, -np.inf], np.nan)
        
        # 2. 每日截面执行 OLS 线性回归提取纯残差
        def _regress_resid(sub_df):
            if len(sub_df) < 30 or sub_df['log_size'].isna().all():
                return sub_df['factor']
            
            y = sub_df['factor'].fillna(0).values
            x = sub_df['log_size'].fillna(sub_df['log_size'].median()).values
            
            # 截面 Z-Score 标准化，防止矩阵条件数过大引发回归崩溃
            y_std, x_std = np.std(y), np.std(x)
            if y_std < 1e-8 or x_std < 1e-8:
                return sub_df['factor']
                
            y = (y - np.mean(y)) / y_std
            x = (x - np.mean(x)) / x_std
            
            # Numpy 极速最小二乘法回归 (y = b*x + c)
            A = np.vstack([x, np.ones(len(x))]).T
            try:
                b, c = np.linalg.lstsq(A, y, rcond=None)[0]
                resid = y - (b * x + c)
                return pd.Series(resid, index=sub_df.index)
            except:
                return sub_df['factor']

        # 执行中性化
        neutralized_factor = df.groupby('date', group_keys=False).apply(_regress_resid)
        return neutralized_factor

    def incremental_deduplication(self, new_factor, factor_pool, dates=None):
        """
        【非线性正交化】：使用 Spearman 秩相关，防止树模型的“特征替代效应”和多重共线性。
        """
        if factor_pool.empty:
            return True, 0.0, None
            
        corrs = []
        most_similar = None
        max_corr = 0.0
        
        if dates is not None:
            df = pd.DataFrame({'new': new_factor, 'date': dates})
            for col in factor_pool.columns:
                df[col] = factor_pool[col].values
                
            for col in factor_pool.columns:
                def _daily_spearman(sub_df):
                    if len(sub_df) < 5: return np.nan
                    return sub_df['new'].corr(sub_df[col], method='spearman')
                    
                daily_corrs = df.groupby('date', group_keys=False).apply(_daily_spearman).dropna()
                if len(daily_corrs) > 0:
                    mean_corr = abs(daily_corrs.mean())
                    if mean_corr > max_corr:
                        max_corr = mean_corr
                        most_similar = col
        else:
            from scipy.stats import spearmanr
            for col in factor_pool.columns:
                corr, _ = spearmanr(new_factor.fillna(0), factor_pool[col].fillna(0))
                if abs(corr) > max_corr:
                    max_corr = abs(corr)
                    most_similar = col
                    
        is_unique = max_corr <= self.threshold
        return is_unique, max_corr, most_similar