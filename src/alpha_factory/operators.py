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
        res = np.where(np.abs(x2) > 0.001, np.divide(x1, x2), 1.0)
        return np.where(np.isfinite(res), res, 1.0)

def _protected_log(x1):
    """保护对数"""
    with np.errstate(invalid='ignore', divide='ignore'):
        res = np.where(x1 > 0.001, np.log(x1), 0.0)
        return np.where(np.isfinite(res), res, 0.0)
        
def _protected_sqrt(x1):
    """保护平方根"""
    with np.errstate(invalid='ignore'):
        res = np.where(x1 > 0.0, np.sqrt(x1), 0.0)
        return np.where(np.isfinite(res), res, 0.0)

def _signed_power(x1, x2):
    """保持符号的幂运算 - 用于放大动量信号"""
    with np.errstate(all='ignore'):
        # 截断指数，防止算子为了拟合而生成负一万或正一万的终极过拟合幂数
        x2_safe = np.clip(x2, -5.0, 5.0)
        # 保护底数，防止出现接近 0 的负数次方导致除零
        x1_safe = np.where((np.abs(x1) < 1e-5) & (x2_safe < 0), np.sign(x1) * 1e-5 + 1e-8, x1)
        res = np.sign(x1_safe) * (np.abs(x1_safe) ** x2_safe)
        return np.where(np.isfinite(res), res, 0.0)

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

# 新增多窗口时序算子
# ts_mean (滚动均值)
def _ts_mean_3(x1):
    return pd.Series(x1).rolling(3).mean().fillna(0).values

def _ts_mean_5(x1):
    return pd.Series(x1).rolling(5).mean().fillna(0).values

def _ts_mean_7(x1):
    return pd.Series(x1).rolling(7).mean().fillna(0).values

def _ts_mean_10(x1):
    return pd.Series(x1).rolling(10).mean().fillna(0).values

def _ts_mean_15(x1):
    return pd.Series(x1).rolling(15).mean().fillna(0).values

def _ts_mean_20(x1):
    return pd.Series(x1).rolling(20).mean().fillna(0).values

def _ts_mean_30(x1):
    return pd.Series(x1).rolling(30).mean().fillna(0).values

# ts_min/ts_max 更多窗口
def _ts_min_3(x1):
    return pd.Series(x1).rolling(3).min().fillna(0).values

def _ts_min_10(x1):
    return pd.Series(x1).rolling(10).min().fillna(0).values

def _ts_min_20(x1):
    return pd.Series(x1).rolling(20).min().fillna(0).values

def _ts_max_3(x1):
    return pd.Series(x1).rolling(3).max().fillna(0).values

def _ts_max_10(x1):
    return pd.Series(x1).rolling(10).max().fillna(0).values

def _ts_max_20(x1):
    return pd.Series(x1).rolling(20).max().fillna(0).values

# ts_sum 更多窗口
def _ts_sum_10(x1):
    return pd.Series(x1).rolling(10).sum().fillna(0).values

def _ts_sum_20(x1):
    return pd.Series(x1).rolling(20).sum().fillna(0).values

# ts_rank 更多窗口
def _ts_rank_3(x1):
    return pd.Series(x1).rolling(3).rank(pct=True).fillna(0.5).values

def _ts_rank_20(x1):
    return pd.Series(x1).rolling(20).rank(pct=True).fillna(0.5).values

# ts_std 更多窗口
def _ts_std_10(x1):
    return pd.Series(x1).rolling(10).std().fillna(0).values

def _ts_std_20(x1):
    return pd.Series(x1).rolling(20).std().fillna(0).values

# 新增高阶时序特征: EWMA (指数移动平均 - 对近期价格极其敏感)
def _ewma_5(x1):
    codes = DataContext.get_codes()
    s = pd.Series(x1)
    if codes is None: return s.ewm(span=5, adjust=False).mean().fillna(0).values
    return s.groupby(codes, sort=False).transform(lambda x: x.ewm(span=5, adjust=False).mean()).fillna(0).values

def _ewma_10(x1):
    codes = DataContext.get_codes()
    s = pd.Series(x1)
    if codes is None: return s.ewm(span=10, adjust=False).mean().fillna(0).values
    return s.groupby(codes, sort=False).transform(lambda x: x.ewm(span=10, adjust=False).mean()).fillna(0).values

def _ewma_20(x1):
    codes = DataContext.get_codes()
    s = pd.Series(x1)
    if codes is None: return s.ewm(span=20, adjust=False).mean().fillna(0).values
    return s.groupby(codes, sort=False).transform(lambda x: x.ewm(span=20, adjust=False).mean()).fillna(0).values

# 新增高阶时序特征: Ts_Zscore (时序标准化 - 极其重要的均值回归指标)
def _ts_zscore_5(x1):
    s = pd.Series(x1)
    return ((s - s.rolling(5).mean()) / (s.rolling(5).std() + 1e-8)).replace([np.inf, -np.inf], 0).fillna(0).values

def _ts_zscore_10(x1):
    s = pd.Series(x1)
    return ((s - s.rolling(10).mean()) / (s.rolling(10).std() + 1e-8)).replace([np.inf, -np.inf], 0).fillna(0).values

def _ts_zscore_20(x1):
    s = pd.Series(x1)
    return ((s - s.rolling(20).mean()) / (s.rolling(20).std() + 1e-8)).replace([np.inf, -np.inf], 0).fillna(0).values

# 新增高阶时序特征: Ts_Return (N日收益率)
def _ts_return_5(x1):
    s = pd.Series(x1)
    return (s.diff(5) / (s.shift(5).abs() + 1e-8)).replace([np.inf, -np.inf], 0).fillna(0).values

def _ts_return_10(x1):
    s = pd.Series(x1)
    return (s.diff(10) / (s.shift(10).abs() + 1e-8)).replace([np.inf, -np.inf], 0).fillna(0).values


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
        # 增加极其微小的容差和极值钳制，严防 x2 接近 0 或 x1 极大带来的 Infinity
        res = np.where(x2 > 1e-5, (x1 / x2) - 1.0, -1.0)
        return np.where(np.isfinite(res), res, -1.0)

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


from src.alpha_factory.context import DataContext
original_make_function = make_function

def custom_make_function(function, name, arity):
    import re
    import pandas as pd
    
    if name == 'rank':
        def wrapper(x1):
            dates = DataContext.get_dates()
            if dates is None:
                return function(x1)
            df = pd.DataFrame({'val': x1, 'date': dates})
            return df.groupby('date')['val'].rank(pct=True).fillna(0.5).values
        wrapper.__name__ = function.__name__
        func_to_register = wrapper
        
    elif name == 'scale':
        # scale必须逐日计算截面和，否则会用未来的总成交量归一化过去的特征，严重漏洞
        def wrapper(x1):
            dates = DataContext.get_dates()
            if dates is None:
                return function(x1)
            df = pd.DataFrame({'val': x1, 'date': dates})
            sums = df.groupby('date')['val'].transform(lambda x: np.nansum(np.abs(x)))
            return (df['val'] / (sums + 0.0001)).replace([np.inf, -np.inf], 0).fillna(0).values
        wrapper.__name__ = function.__name__
        func_to_register = wrapper
        
    elif name == 'truncate':
        # truncate也必须逐日截面计算分位数，防未来信息穿越
        def wrapper(x1):
            dates = DataContext.get_dates()
            if dates is None:
                return function(x1)
            df = pd.DataFrame({'val': x1, 'date': dates})
            def _trunc(x):
                valid_x = x.dropna()
                if len(valid_x) == 0: return x
                p1, p99 = np.nanpercentile(valid_x, 1), np.nanpercentile(valid_x, 99)
                return np.clip(x, p1, p99)
            return df.groupby('date')['val'].transform(_trunc).values
        wrapper.__name__ = function.__name__
        func_to_register = wrapper
        
    elif name == 'indneu':
        func_to_register = function
        
    else:
        m = re.search(r'_(\d+)$', function.__name__)
        if m:
            window = int(m.group(1))
            # 修复时序算子跨股票偏移泄露 BUG: delay, delta, return 需要跨跃过去的 N 天，意味着涉及 N+1 天的数据周期
            if any(k in function.__name__ for k in ['delay', 'delta', 'return']):
                window += 1
            if arity == 1:
                def wrapper(x1):
                    res = function(x1)
                    return DataContext.mask_invalid_ts(res, window)
            elif arity == 2:
                def wrapper(x1, x2):
                    res = function(x1, x2)
                    return DataContext.mask_invalid_ts(res, window)
            elif arity == 3:
                def wrapper(x1, x2, x3):
                    res = function(x1, x2, x3)
                    return DataContext.mask_invalid_ts(res, window)
            else:
                wrapper = function
            wrapper.__name__ = function.__name__
            func_to_register = wrapper
        else:
            func_to_register = function
            
    return original_make_function(function=func_to_register, name=name, arity=arity)

# Override make_function in this module namespace
make_function = custom_make_function

# 基础运算 (4个)

protected_div = make_function(function=_protected_div, name='div', arity=2)
protected_log = make_function(function=_protected_log, name='log', arity=1)
protected_sqrt = make_function(function=_protected_sqrt, name='sqrt', arity=1)
signed_power = make_function(function=_signed_power, name='signpow', arity=2)

# 时序算子
ts_rank_3 = make_function(function=_ts_rank_3, name='tsrank3', arity=1)
ts_rank_5 = make_function(function=_ts_rank_5, name='tsrank5', arity=1)
ts_rank_10 = make_function(function=_ts_rank_10, name='tsrank10', arity=1)
ts_rank_20 = make_function(function=_ts_rank_20, name='tsrank20', arity=1)

ts_mean_3 = make_function(function=_ts_mean_3, name='tsmean3', arity=1)
ts_mean_5 = make_function(function=_ts_mean_5, name='tsmean5', arity=1)
ts_mean_7 = make_function(function=_ts_mean_7, name='tsmean7', arity=1)
ts_mean_10 = make_function(function=_ts_mean_10, name='tsmean10', arity=1)
ts_mean_15 = make_function(function=_ts_mean_15, name='tsmean15', arity=1)
ts_mean_20 = make_function(function=_ts_mean_20, name='tsmean20', arity=1)
ts_mean_30 = make_function(function=_ts_mean_30, name='tsmean30', arity=1)

decay_linear_5 = make_function(function=_decay_linear_5, name='decay5', arity=1)
decay_linear_10 = make_function(function=_decay_linear_10, name='decay10', arity=1)

ts_min_3 = make_function(function=_ts_min_3, name='tsmin3', arity=1)
ts_min_5 = make_function(function=_ts_min_5, name='tsmin5', arity=1)
ts_min_10 = make_function(function=_ts_min_10, name='tsmin10', arity=1)
ts_min_20 = make_function(function=_ts_min_20, name='tsmin20', arity=1)

ts_max_3 = make_function(function=_ts_max_3, name='tsmax3', arity=1)
ts_max_5 = make_function(function=_ts_max_5, name='tsmax5', arity=1)
ts_max_10 = make_function(function=_ts_max_10, name='tsmax10', arity=1)
ts_max_20 = make_function(function=_ts_max_20, name='tsmax20', arity=1)

ts_argmax_5 = make_function(function=_ts_argmax_5, name='tsargmax5', arity=1)
ts_argmin_5 = make_function(function=_ts_argmin_5, name='tsargmin5', arity=1)

ts_sum_5 = make_function(function=_ts_sum_5, name='tssum5', arity=1)
ts_sum_10 = make_function(function=_ts_sum_10, name='tssum10', arity=1)
ts_sum_20 = make_function(function=_ts_sum_20, name='tssum20', arity=1)

ts_stddev_5 = make_function(function=_ts_stddev_5, name='tsstd5', arity=1)
ts_std_10 = make_function(function=_ts_std_10, name='tsstd10', arity=1)
ts_std_20 = make_function(function=_ts_std_20, name='tsstd20', arity=1)

ts_delay_1 = make_function(function=_ts_delay_1, name='delay1', arity=1)
ts_delay_5 = make_function(function=_ts_delay_5, name='delay5', arity=1)
ts_delta_1 = make_function(function=_ts_delta_1, name='delta1', arity=1)

# 新增时序
ts_skewness_5 = make_function(function=_ts_skewness_5, name='skew5', arity=1)
ts_kurtosis_5 = make_function(function=_ts_kurtosis_5, name='kurt5', arity=1)
ts_mad_5 = make_function(function=_ts_mad_5, name='mad5', arity=1)

# 注册新增高阶时序算子
ewma_5 = make_function(function=_ewma_5, name='ewma5', arity=1)
ewma_10 = make_function(function=_ewma_10, name='ewma10', arity=1)
ewma_20 = make_function(function=_ewma_20, name='ewma20', arity=1)

ts_zscore_5 = make_function(function=_ts_zscore_5, name='tszscore5', arity=1)
ts_zscore_10 = make_function(function=_ts_zscore_10, name='tszscore10', arity=1)
ts_zscore_20 = make_function(function=_ts_zscore_20, name='tszscore20', arity=1)

ts_return_5 = make_function(function=_ts_return_5, name='tsret5', arity=1)
ts_return_10 = make_function(function=_ts_return_10, name='tsret10', arity=1)


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

# 汇总算子列表 (扩展版 - 支持更多 WQ101 因子)
custom_operations = [
    # 基础数学
    protected_div, protected_log, protected_sqrt, signed_power,
    
    # 时序算子 (多窗口)
    ts_rank_3, ts_rank_5, ts_rank_10, ts_rank_20,
    ts_mean_3, ts_mean_5, ts_mean_7, ts_mean_10, ts_mean_15, ts_mean_20, ts_mean_30,
    decay_linear_5, decay_linear_10,
    ts_min_3, ts_min_5, ts_min_10, ts_min_20,
    ts_max_3, ts_max_5, ts_max_10, ts_max_20,
    ts_argmax_5, ts_argmin_5,
    ts_sum_5, ts_sum_10, ts_sum_20,
    ts_stddev_5, ts_std_10, ts_std_20,
    ts_delay_1, ts_delay_5, ts_delta_1,
    ts_skewness_5, ts_kurtosis_5, ts_mad_5,
    ewma_5, ewma_10, ewma_20,
    ts_zscore_5, ts_zscore_10, ts_zscore_20,
    ts_return_5, ts_return_10,
    
    # 截面算子
    rank, scale, truncate, ind_neutralize,
    
    # 逻辑/特色算子
    condition, abs_val, limit_distance,
    
    # 关联算子
    correlation_5, covariance_5
]
