import numpy as np
import pandas as pd

class DataContext:
    """
    全局数据上下文，用于向 gplearn 的函数注入股票代码(code)和日期(date)信息，
    从而解决时序算子跨股票污染和截面算子无法按交易日对齐的根本缺陷。
    同时存储已发现的优质因子池，供多目标适应度惩罚项计算使用。
    """
    _codes = None
    _dates = None
    _masks = {}  # 缓存的掩码: mask[window] = boolean array
    _factor_pool = None  # numpy array (n_samples, n_factors) — 已通过质量门控的因子截面值
    
    @classmethod
    def set_context(cls, codes, dates):
        """
        每次 fit 或 transform 前调用，设置当前的上下文环境
        """
        cls._codes = np.array(codes)
        cls._dates = np.array(dates)
        cls._masks = {}
        
    @classmethod
    def get_codes(cls):
        return cls._codes
        
    @classmethod
    def get_dates(cls):
        return cls._dates

    @classmethod
    def set_factor_pool(cls, factor_array: np.ndarray):
        """
        保存已发现的优质因子池（截面值），供适应度相关性惩罚项使用。
        factor_array: shape (n_samples, n_factors)
        """
        cls._factor_pool = factor_array

    @classmethod
    def get_factor_pool(cls):
        """返回已有因子池 numpy array，如果为空则返回 None。"""
        return cls._factor_pool


    @classmethod
    def get_mask(cls, window):
        """
        获取一个布尔掩码，如果当前行 [i] 与 [i - window + 1] 属于同一只股票则为 True
        必须要求传入的数据是先按 code 排序，再按 date 排序的！
        """
        if window in cls._masks:
            return cls._masks[window]
            
        if cls._codes is None:
            # 安全后备: 如果没有设置上下文，允许全部通过
            return slice(None)
            
        # 比较当前的 code 和 window-1 天前的 code 是否一样
        # 如果一样，说明这 window 天的数据都属于同一只股票，跨股票污染被隔离
        shift_codes = pd.Series(cls._codes).shift(window - 1).values
        mask = (cls._codes == shift_codes)
        cls._masks[window] = mask
        return mask
    
    @classmethod
    def mask_invalid_ts(cls, array, window, default_val=0.0):
        """
        使用掩码清理时序污染数据
        """
        if cls._codes is None:
            return array
        mask = cls.get_mask(window)
        # 用 np.where 替换为 default_val
        return np.where(mask, array, default_val)
