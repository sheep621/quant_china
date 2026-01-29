import numpy as np
import pandas as pd
from gplearn.functions import make_function

# ======================
# 1. 基础数学算子
# ======================

def _protected_div(x1, x2):
    """保护除法,避免除零"""
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(np.abs(x2) > 0.001, np.divide(x1, x2), 1.)

def _protected_log(x1):
    """保护对数"""
    with np.errstate(invalid='ignore'):
        return np.where(x1 > 0.001, np.log(x1), 0.)
        
def _protected_sqrt(x1):
    """保护平方根"""
    with np.errstate(invalid='ignore'):
        return np.where(x1 > 0., np.sqrt(x1), 0.)

def _signed_power(x1, x2):
    """保持符号的幂运算 - 用于放大动量信号"""
    with np.errstate(invalid='ignore'):
        return np.sign(x1) * (np.abs(x1) ** x2)

# ======================
# 2. 时序算子 (简化版)
# ======================

def _ts_delay_1(x1): 
    """滞后1期"""
    return np.roll(x1, 1)

def _ts_delay_5(x1): 
    """滞后5期"""
    return np.roll(x1, 5)

def _ts_delta_1(x1): 
    """差分(Delta)"""
    return x1 - np.roll(x1, 1)

def _ts_stddev(x1):
    """滚动标准差近似 - 用当前值减去延迟值的标准差"""
    delayed = np.roll(x1, 5)
    return np.abs(x1 - delayed)

# ======================
# 3. 截面算子 (Rank核心)
# ======================

def _rank(x1):
    """
    百分位排名 - WQ101核心算子
    去除绝对值影响,只保留相对强弱
    """
    return pd.Series(x1).rank(pct=True).fillna(0.5).values

def _scale(x1):
    """
    归一化 - 使sum(abs(x))=1
    用于构建市值中性组合
    """
    s = np.nansum(np.abs(x1))
    return x1 / (s + 0.0001)

# ======================  
# 4. A股专用算子
# ======================

def _limit_dist_up(close, pre_close):
    """
    距离涨停板距离
    正值=距离涨停远,负值=已涨停或接近
    """
    limit_up = pre_close * 1.10  # A股10%涨停
    return (limit_up - close) / (pre_close * 0.10 + 0.0001)

def _limit_dist_down(close, pre_close):
    """
    距离跌停板距离  
    正值=距离跌停远,负值=已跌停或接近
    """
    limit_down = pre_close * 0.90  # A股10%跌停
    return (close - limit_down) / (pre_close * 0.10 + 0.0001)

def _truncate(x1):
    """
    Winsorize截断 - 去极值
    将outlier限制在1%, 99%分位
    """
    p1 = np.nanpercentile(x1, 1)
    p99 = np.nanpercentile(x1, 99)
    return np.clip(x1, p1, p99)

# ======================
# 高级统计算子
# ======================

def _correlation(x1, x2):
    """
    相关性近似 - 用符号一致性代替
    真实Corr需要窗口,这里简化为同向性
    """
    return np.sign(x1) * np.sign(x2)

# ======================
# 注册为gplearn函数
# ======================

# 基础运算
protected_div = make_function(function=_protected_div, name='div', arity=2)
protected_log = make_function(function=_protected_log, name='log', arity=1)
protected_sqrt = make_function(function=_protected_sqrt, name='sqrt', arity=1)
signed_power = make_function(function=_signed_power, name='signpow', arity=2)

# 时序算子
ts_delay_1 = make_function(function=_ts_delay_1, name='delay1', arity=1)
ts_delay_5 = make_function(function=_ts_delay_5, name='delay5', arity=1)
ts_delta_1 = make_function(function=_ts_delta_1, name='delta1', arity=1)
ts_stddev = make_function(function=_ts_stddev, name='tsstd', arity=1)

# 截面算子  
rank = make_function(function=_rank, name='rank', arity=1)
scale = make_function(function=_scale, name='scale', arity=1)
truncate = make_function(function=_truncate, name='trunc', arity=1)

# 关联算子
correlation = make_function(function=_correlation, name='corr', arity=2)

# 汇总算子列表
custom_operations = [
    # 数学
    protected_div, protected_log, protected_sqrt, signed_power,
    # 时序  
    ts_delay_1, ts_delay_5, ts_delta_1, ts_stddev,
    # 截面
    rank, scale, truncate,
    # 关联
    correlation
]
