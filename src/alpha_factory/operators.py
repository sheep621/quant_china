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
# 2. 时序算子 (核心!WQ101重点)
# ======================

def _ts_rank_5(x1):
    """
    ⭐⭐⭐⭐⭐ Ts_Rank - 滚动排名(5期)
    文档:"最强大的非线性算子,剥离绝对水平,只关注相对强弱"
    计算当前值在过去5天的百分位排名
    """
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        window = x1[i-4:i+1]
        result[i] = pd.Series(window).rank(pct=True).iloc[-1]
    return result

def _ts_rank_10(x1):
    """Ts_Rank - 10期窗口"""
    result = np.zeros_like(x1)
    for i in range(9, len(x1)):
        window = x1[i-9:i+1]
        result[i] = pd.Series(window).rank(pct=True).iloc[-1]
    return result

def _decay_linear_5(x1):
    """
    ⭐⭐⭐⭐ Decay_Linear - 线性衰减加权(5期)
    文档:"给予近期数据更高权重,降低滞后性"
    权重: [1, 2, 3, 4, 5] 归一化
    """
    weights = np.array([1, 2, 3, 4, 5])
    weights = weights / weights.sum()
    
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        window = x1[i-4:i+1]
        result[i] = np.dot(window, weights)
    return result

def _decay_linear_10(x1):
    """Decay_Linear - 10期窗口"""
    weights = np.arange(1, 11)
    weights = weights / weights.sum()
    
    result = np.zeros_like(x1)
    for i in range(9, len(x1)):
        window = x1[i-9:i+1]
        result[i] = np.dot(window, weights)
    return result

def _ts_min_5(x1):
    """滚动最小值(5期)"""
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        result[i] = np.min(x1[i-4:i+1])
    return result

def _ts_max_5(x1):
    """滚动最大值(5期)"""
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        result[i] = np.max(x1[i-4:i+1])
    return result

def _ts_argmax_5(x1):
    """
    ⭐⭐⭐ Ts_ArgMax - 极值位置(5期)
    返回过去5天最大值的位置(0=今天,4=5天前)
    """
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        window = x1[i-4:i+1]
        result[i] = len(window) - 1 - np.argmax(window)  # 倒序:0=最近
    return result

def _ts_argmin_5(x1):
    """Ts_ArgMin - 最小值位置(5期)"""
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        window = x1[i-4:i+1]
        result[i] = len(window) - 1 - np.argmin(window)
    return result

def _ts_sum_5(x1):
    """滚动求和(5期)"""
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        result[i] = np.sum(x1[i-4:i+1])
    return result

# 原有简单时序算子
def _ts_delay_1(x1): 
    """滞后1期"""
    return np.roll(x1, 1)

def _ts_delay_5(x1): 
    """滞后5期"""
    return np.roll(x1, 5)

def _ts_delta_1(x1): 
    """差分(Delta)"""
    return x1 - np.roll(x1, 1)

def _ts_stddev_5(x1):
    """滚动标准差(5期)"""
    result = np.zeros_like(x1)
    for i in range(4, len(x1)):
        result[i] = np.std(x1[i-4:i+1])
    return result

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

def _truncate(x1):
    """
    Winsorize截断 - 去极值
    将outlier限制在1%, 99%分位
    """
    p1 = np.nanpercentile(x1, 1)
    p99 = np.nanpercentile(x1, 99)
    return np.clip(x1, p1, p99)

# ======================  
# 4. 逻辑/条件算子
# ======================

def _condition(x1, x2, x3):
    """
    ⭐⭐⭐ If-Then-Else条件逻辑
    If x1>0: return x2, else: return x3
    用于处理涨跌停等状态依赖策略
    """
    return np.where(x1 > 0, x2, x3)

def _abs_val(x1):
    """绝对值"""
    return np.abs(x1)

# ======================
# 5. 高级统计算子
# ======================

def _correlation_5(x1, x2):
    """
    滚动相关性(5期)
    计算两序列的Pearson相关
    """
    result = np.zeros(len(x1))
    for i in range(4, len(x1)):
        w1 = x1[i-4:i+1]
        w2 = x2[i-4:i+1]
        if np.std(w1) > 0 and np.std(w2) > 0:
            result[i] = np.corrcoef(w1, w2)[0, 1]
    return result

def _covariance_5(x1, x2):
    """滚动协方差(5期)"""
    result = np.zeros(len(x1))
    for i in range(4, len(x1)):
        w1 = x1[i-4:i+1]
        w2 = x2[i-4:i+1]
        result[i] = np.cov(w1, w2)[0, 1]
    return result

# ======================
# 注册为gplearn函数
# ======================

# 基础运算 (4个)
protected_div = make_function(function=_protected_div, name='div', arity=2)
protected_log = make_function(function=_protected_log, name='log', arity=1)
protected_sqrt = make_function(function=_protected_sqrt, name='sqrt', arity=1)
signed_power = make_function(function=_signed_power, name='signpow', arity=2)

# 时序算子 (13个) ⭐核心区
ts_rank_5 = make_function(function=_ts_rank_5, name='tsrank5', arity=1)
ts_rank_10 = make_function(function=_ts_rank_10, name='tsrank10', arity=1)
decay_linear_5 = make_function(function=_decay_linear_5, name='decay5', arity=1)
decay_linear_10 = make_function(function=_decay_linear_10, name='decay10', arity=1)
ts_min_5 = make_function(function=_ts_min_5, name='tsmin5', arity=1)
ts_max_5 = make_function(function=_ts_max_5, name='tsmax5', arity=1)
ts_argmax_5 = make_function(function=_ts_argmax_5, name='tsargmax5', arity=1)
ts_argmin_5 = make_function(function=_ts_argmin_5, name='tsargmin5', arity=1)
ts_sum_5 = make_function(function=_ts_sum_5, name='tssum5', arity=1)
ts_delay_1 = make_function(function=_ts_delay_1, name='delay1', arity=1)
ts_delay_5 = make_function(function=_ts_delay_5, name='delay5', arity=1)
ts_delta_1 = make_function(function=_ts_delta_1, name='delta1', arity=1)
ts_stddev_5 = make_function(function=_ts_stddev_5, name='tsstd5', arity=1)

# 截面算子 (3个)
rank = make_function(function=_rank, name='rank', arity=1)
scale = make_function(function=_scale, name='scale', arity=1)
truncate = make_function(function=_truncate, name='trunc', arity=1)

# 逻辑算子 (2个)
condition = make_function(function=_condition, name='if', arity=3)
abs_val = make_function(function=_abs_val, name='abs', arity=1)

# 关联算子 (2个)
correlation_5 = make_function(function=_correlation_5, name='corr5', arity=2)
covariance_5 = make_function(function=_covariance_5, name='cov5', arity=2)

# 汇总算子列表 (24个自定义算子 + 5个gplearn基础 = 29个总计)
custom_operations = [
    # 基础数学 (4)
    protected_div, protected_log, protected_sqrt, signed_power,
    
    # 时序核心 (13) ⭐⭐⭐
    ts_rank_5, ts_rank_10,           # Rank系列
    decay_linear_5, decay_linear_10, # Decay系列
    ts_min_5, ts_max_5,               # Min/Max
    ts_argmax_5, ts_argmin_5,         # ArgMax/Min
    ts_sum_5, ts_stddev_5,            # Sum/Std
    ts_delay_1, ts_delay_5, ts_delta_1,  # Delay/Delta
    
    # 截面 (3)
    rank, scale, truncate,
    
    # 逻辑 (2)
    condition, abs_val,
    
    # 关联 (2)
    correlation_5, covariance_5
]

print(f"✅ Loaded {len(custom_operations)} custom operators for Alpha Mining")
