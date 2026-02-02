import numpy as np
import pandas as pd
from gplearn.functions import make_function
from scipy.stats import skew, kurtosis

# ======================
# 1. 基础数学算子
# ======================

def _protected_div(x1, x2):
    """保护除法,避免除零"""
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(np.abs(x2) > 0.001, np.divide(x1, x2), 1.)

def _protected_log(x1):
    """保护对数"""
    with np.errstate(invalid='ignore', divide='ignore'):
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
# 2. 时序算子 (向量化优化版)
# ======================

def _ts_rank_5(x1):
    """Ts_Rank - 滚动排名(5期) - 向量化优化"""
    return pd.Series(x1).rolling(5).rank(pct=True).fillna(0.5).values

def _ts_rank_10(x1):
    """Ts_Rank - 10期窗口 - 向量化优化"""
    return pd.Series(x1).rolling(10).rank(pct=True).fillna(0.5).values

def _decay_linear_5(x1):
    """Decay_Linear - 线性衰减加权(5期)"""
    weights = np.array([1, 2, 3, 4, 5])
    weights = weights / weights.sum()
    # 使用卷积实现快速加权移动平均
    return np.convolve(x1, weights[::-1], mode='full')[:len(x1)]

def _decay_linear_10(x1):
    """Decay_Linear - 10期窗口"""
    weights = np.arange(1, 11)
    weights = weights / weights.sum()
    return np.convolve(x1, weights[::-1], mode='full')[:len(x1)]

def _ts_min_5(x1):
    """滚动最小值(5期)"""
    return pd.Series(x1).rolling(5).min().fillna(0).values

def _ts_max_5(x1):
    """滚动最大值(5期)"""
    return pd.Series(x1).rolling(5).max().fillna(0).values

def _ts_argmax_5(x1):
    """Ts_ArgMax - 极值位置(5期)"""
    # rolling().apply is slow, but ArgMax is hard to fully vectorize without stride tricks
    # using a simplified approach or accepting the apply overhead
    return pd.Series(x1).rolling(5).apply(np.argmax, raw=True).fillna(0).values

def _ts_argmin_5(x1):
    """Ts_ArgMin - 最小值位置(5期)"""
    return pd.Series(x1).rolling(5).apply(np.argmin, raw=True).fillna(0).values

def _ts_sum_5(x1):
    """滚动求和(5期)"""
    return pd.Series(x1).rolling(5).sum().fillna(0).values

def _ts_stddev_5(x1):
    """滚动标准差(5期)"""
    return pd.Series(x1).rolling(5).std().fillna(0).values

# 新增高阶时序算子
def _ts_skewness_5(x1):
    """滚动偏度(5期) - 捕捉非线性特征"""
    return pd.Series(x1).rolling(5).skew().fillna(0).values

def _ts_kurtosis_5(x1):
    """滚动峰度(5期) - 捕捉极端风险"""
    return pd.Series(x1).rolling(5).kurt().fillna(0).values

def _ts_mad_5(x1):
    """
    滚动稳健偏差(MAD) - 抗噪能力优于StdDev
    MAD = Median(|x - Median(x)|)
    """
    # 效率权衡: 使用apply计算真实MAD
    def mad(x):
        return np.median(np.abs(x - np.median(x)))
    return pd.Series(x1).rolling(5).apply(mad, raw=True).fillna(0).values

# 原有简单时序算子
def _ts_delay_1(x1): 
    return np.roll(x1, 1)

def _ts_delay_5(x1): 
    return np.roll(x1, 5)

def _ts_delta_1(x1): 
    return x1 - np.roll(x1, 1)

# ======================
# 3. 截面算子
# ======================

def _rank(x1):
    return pd.Series(x1).rank(pct=True).fillna(0.5).values

def _scale(x1):
    s = np.nansum(np.abs(x1))
    return x1 / (s + 0.0001)

def _truncate(x1):
    p1 = np.nanpercentile(x1, 1)
    p99 = np.nanpercentile(x1, 99)
    return np.clip(x1, p1, p99)

def _ind_neutralize(x1, x2):
    """
    行业中性化
    x1: 因子值
    x2: 行业/分组代码
    """
    # 简单的去均值处理
    # 注意: 这里假设x1, x2长度一致且一一对应
    # 由于gplearn传入的是numpy array，我们需要转DataFrame做groupby
    try:
        df = pd.DataFrame({'val': x1, 'grp': x2})
        # 填充NaN分组
        df['grp'] = df['grp'].fillna(-1)
        # 组内去均值
        neutralized = df.groupby('grp')['val'].transform(lambda x: x - x.mean())
        return neutralized.fillna(0).values
    except:
        return x1 # Fallback

# ======================  
# 4. 逻辑/条件算子
# ======================

def _condition(x1, x2, x3):
    return np.where(x1 > 0, x2, x3)

def _abs_val(x1):
    return np.abs(x1)

def _limit_distance(x1, x2):
    """
    涨停距离算子
    x1: 收盘价/当前价
    x2: 涨停价 (High Limit)
    Return: 距离涨停板的百分比 (负数)
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        # 距离 = (Close / Limit) - 1
        # 越接近0表示越接近涨停
        return np.where(x2 > 0, (x1 / x2) - 1.0, -1.0)

# ======================
# 5. 高级统计算子
# ======================

def _correlation_5(x1, x2):
    """滚动相关性(5期)"""
    return pd.Series(x1).rolling(5).corr(pd.Series(x2)).fillna(0).values

def _covariance_5(x1, x2):
    """滚动协方差(5期)"""
    return pd.Series(x1).rolling(5).cov(pd.Series(x2)).fillna(0).values

# ======================
# 注册为gplearn函数
# ======================

# 基础运算 (4个)
protected_div = make_function(function=_protected_div, name='div', arity=2)
protected_log = make_function(function=_protected_log, name='log', arity=1)
protected_sqrt = make_function(function=_protected_sqrt, name='sqrt', arity=1)
signed_power = make_function(function=_signed_power, name='signpow', arity=2)

# 时序算子
ts_rank_5 = make_function(function=_ts_rank_5, name='tsrank5', arity=1)
ts_rank_10 = make_function(function=_ts_rank_10, name='tsrank10', arity=1)
decay_linear_5 = make_function(function=_decay_linear_5, name='decay5', arity=1)
decay_linear_10 = make_function(function=_decay_linear_10, name='decay10', arity=1)
ts_min_5 = make_function(function=_ts_min_5, name='tsmin5', arity=1)
ts_max_5 = make_function(function=_ts_max_5, name='tsmax5', arity=1)
ts_argmax_5 = make_function(function=_ts_argmax_5, name='tsargmax5', arity=1)
ts_argmin_5 = make_function(function=_ts_argmin_5, name='tsargmin5', arity=1)
ts_sum_5 = make_function(function=_ts_sum_5, name='tssum5', arity=1)
ts_stddev_5 = make_function(function=_ts_stddev_5, name='tsstd5', arity=1)
ts_delay_1 = make_function(function=_ts_delay_1, name='delay1', arity=1)
ts_delay_5 = make_function(function=_ts_delay_5, name='delay5', arity=1)
ts_delta_1 = make_function(function=_ts_delta_1, name='delta1', arity=1)

# 新增时序
ts_skewness_5 = make_function(function=_ts_skewness_5, name='skew5', arity=1)
ts_kurtosis_5 = make_function(function=_ts_kurtosis_5, name='kurt5', arity=1)
ts_mad_5 = make_function(function=_ts_mad_5, name='mad5', arity=1)

# 截面算子
rank = make_function(function=_rank, name='rank', arity=1)
scale = make_function(function=_scale, name='scale', arity=1)
truncate = make_function(function=_truncate, name='trunc', arity=1)
ind_neutralize = make_function(function=_ind_neutralize, name='indneu', arity=2) # Arity=2

# 逻辑/特色算子
condition = make_function(function=_condition, name='if', arity=3)
abs_val = make_function(function=_abs_val, name='abs', arity=1)
limit_distance = make_function(function=_limit_distance, name='limdist', arity=2)

# 关联算子
correlation_5 = make_function(function=_correlation_5, name='corr5', arity=2)
covariance_5 = make_function(function=_covariance_5, name='cov5', arity=2)

# 汇总算子列表
custom_operations = [
    # 基础数学
    protected_div, protected_log, protected_sqrt, signed_power,
    
    # 时序
    ts_rank_5, ts_rank_10, decay_linear_5, decay_linear_10,
    ts_min_5, ts_max_5, ts_argmax_5, ts_argmin_5, ts_sum_5, ts_stddev_5,
    ts_delay_1, ts_delay_5, ts_delta_1,
    ts_skewness_5, ts_kurtosis_5, ts_mad_5, # New
    
    # 截面
    rank, scale, truncate, ind_neutralize, # New
    
    # 逻辑/特色
    condition, abs_val, limit_distance, # New
    
    # 关联
    correlation_5, covariance_5
]
