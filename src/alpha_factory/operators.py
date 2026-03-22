import numpy as np
from gplearn.functions import make_function
from src.alpha_factory.context import DataContext

# ==============================================================================
# 内部辅助函数：极速获取每日截面索引缓存 (用于截面算子)
# ==============================================================================
def _get_date_indices():
    dates = DataContext.get_dates()
    if dates is None:
        return []
    
    # 动态构建并缓存每日数据的切片索引，将时间复杂度降为 O(1)
    if not hasattr(DataContext, '_cached_operator_date_indices'):
        unique_dates, inverse = np.unique(dates, return_inverse=True)
        DataContext._cached_operator_date_indices = [np.where(inverse == i)[0] for i in range(len(unique_dates))]
        
    return DataContext._cached_operator_date_indices

# ==============================================================================
# 第一部分：极速 Numpy 时序算子 (Time-Series Operators)
# 彻底抛弃 Pandas groupby.rolling，利用 DataContext.mask 和 np.roll 实现 50 倍提速
# ==============================================================================

def make_ts_delay(window):
    def _ts_delay(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = np.roll(x, window)
        # 如果 window=1，必须保证当前行和前 1 行属于同一只股票，所以 mask_window=2
        return DataContext.mask_invalid_ts(res, window + 1, default_val=0.0)
    return _ts_delay

def make_ts_delta(window):
    def _ts_delta(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        delayed = np.roll(x, window)
        res = x - delayed
        return DataContext.mask_invalid_ts(res, window + 1, default_val=0.0)
    return _ts_delta

def make_ts_mean(window):
    def _ts_mean(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = np.zeros_like(x)
        for i in range(window):
            res += np.roll(x, i)
        res /= window
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_mean

def make_ts_max(window):
    def _ts_max(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = x.copy()
        for i in range(1, window):
            res = np.maximum(res, np.roll(x, i))
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_max

def make_ts_min(window):
    def _ts_min(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = x.copy()
        for i in range(1, window):
            res = np.minimum(res, np.roll(x, i))
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_min

def make_ts_std(window):
    def _ts_std(x):
        x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        sum_x = np.zeros_like(x)
        sum_x2 = np.zeros_like(x)
        for i in range(window):
            rolled = np.roll(x, i)
            sum_x += rolled
            sum_x2 += rolled ** 2
        mean_x = sum_x / window
        var_x = (sum_x2 / window) - (mean_x ** 2)
        var_x = np.maximum(var_x, 0.0) # 防止浮点误差导致负数
        res = np.sqrt(var_x)
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_std

def make_ts_corr(window):
    def _ts_corr(x, y):
        x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        y = np.clip(np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        sum_x = np.zeros_like(x); sum_y = np.zeros_like(y)
        sum_xy = np.zeros_like(x); sum_x2 = np.zeros_like(x); sum_y2 = np.zeros_like(y)
        
        for i in range(window):
            rx = np.roll(x, i)
            ry = np.roll(y, i)
            sum_x += rx
            sum_y += ry
            sum_xy += rx * ry
            sum_x2 += rx ** 2
            sum_y2 += ry ** 2
            
        mean_x = sum_x / window
        mean_y = sum_y / window
        cov = (sum_xy / window) - (mean_x * mean_y)
        var_x = np.maximum((sum_x2 / window) - (mean_x ** 2), 1e-8)
        var_y = np.maximum((sum_y2 / window) - (mean_y ** 2), 1e-8)
        
        res = cov / np.sqrt(var_x * var_y)
        res = np.clip(np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_corr


# ==============================================================================
# 第二部分：横截面算子 (Cross-Sectional Operators)
# 强制剥离市场 Beta，输出时间中性的纯 Alpha 相对强度
# ==============================================================================

def _cs_rank(x):
    """截面排序归一化 (输出 0 到 1 之间的相对排名)"""
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    indices = _get_date_indices()
    if not indices: return x
    
    res = np.zeros_like(x, dtype=float)
    for idx in indices:
        slice_x = x[idx]
        if len(slice_x) > 1:
            # 两次 argsort 即为排名
            ranks = np.argsort(np.argsort(slice_x))
            res[idx] = ranks / (len(slice_x) - 1)
    return res

def _cs_zscore(x):
    """截面 Z-Score 标准化"""
    x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
    indices = _get_date_indices()
    if not indices: return x
    
    res = np.zeros_like(x, dtype=float)
    for idx in indices:
        slice_x = x[idx]
        std = np.std(slice_x)
        if std > 1e-8:
            res[idx] = (slice_x - np.mean(slice_x)) / std
        else:
            res[idx] = 0.0
    return np.clip(np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)

def _cs_mad(x):
    """截面 MAD 去极值 (Median Absolute Deviation)"""
    x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
    indices = _get_date_indices()
    if not indices: return x
    
    res = np.zeros_like(x, dtype=float)
    for idx in indices:
        slice_x = x[idx]
        median = np.median(slice_x)
        mad = np.median(np.abs(slice_x - median))
        if mad > 1e-8:
            upper = median + 3 * 1.4826 * mad
            lower = median - 3 * 1.4826 * mad
            res[idx] = np.clip(slice_x, lower, upper)
        else:
            res[idx] = slice_x
    return np.clip(np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)

def _sign(x):
    """符号函数：提取趋势方向"""
    return np.sign(np.nan_to_num(x, nan=0.0))

def make_ts_sum(window):
    """
    Ts_Sum: 过去 window 天的累加值。
    依据：极度常用于成交量(Volume)和换手率的聚合。
    """
    def _ts_sum(x):
        x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        res = np.zeros_like(x)
        for i in range(window):
            res += np.roll(x, i)
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_sum

def make_ts_decay_linear(window):
    """
    Ts_Decay_Linear: 线性衰减加权移动平均。
    依据：WorldQuant 101 核心算子。距离今天越近的数据权重越大（今天权重为d, 昨天d-1...）。
    比普通 ts_mean 反应更灵敏，有效防止均线滞后。
    """
    def _ts_decay_linear(x):
        x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        res = np.zeros_like(x)
        weight_sum = (window * (window + 1)) / 2.0
        for i in range(window):
            weight = window - i
            res += np.roll(x, i) * weight
        res /= weight_sum
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_decay_linear


def make_ts_rank(window):
    """
    Ts_Rank: 当天数值在过去 window 天中的时间序列百分位排名。
    依据：Qlib 核心算子。用于衡量“今天处于最近一个月的什么水平”，比绝对数值更能抵御宏观漂移。
    """
    def _ts_rank(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = np.zeros_like(x)
        for i in range(window):
            # 计算过去 d 天中有多少天小于等于今天的值
            res += (x >= np.roll(x, i)).astype(float)
        res = res / window
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_rank

def make_ts_argmax(window):
    """
    Ts_ArgMax: 过去 window 天的最大值发生在前几天（0代表今天，1代表昨天）。
    依据：WorldQuant 经典形态算子。寻找“创出新高后的回调天数”。
    """
    def _ts_argmax(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = np.zeros_like(x)
        max_val = x.copy()
        for i in range(1, window):
            rolled = np.roll(x, i)
            # 找到更大的值，更新最大值并记录天数
            update_mask = rolled > max_val
            max_val[update_mask] = rolled[update_mask]
            res[update_mask] = i
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_argmax

def make_ts_argmin(window):
    """
    Ts_ArgMin: 过去 window 天的最小值发生在前几天。
    """
    def _ts_argmin(x):
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        res = np.zeros_like(x)
        min_val = x.copy()
        for i in range(1, window):
            rolled = np.roll(x, i)
            update_mask = rolled < min_val
            min_val[update_mask] = rolled[update_mask]
            res[update_mask] = i
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_argmin


def _cs_scale(x):
    """
    CS_Scale: 截面归一化，使得所有股票的绝对值之和为 1。
    依据：WorldQuant 101 的标配收尾算子。它保持了因子的多空方向，并直接将其转化为投资组合的持仓权重（Risk Parity 雏形）。
    """
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    indices = _get_date_indices()
    if not indices: return x
    
    res = np.zeros_like(x, dtype=float)
    for idx in indices:
        slice_x = x[idx]
        sum_abs = np.sum(np.abs(slice_x))
        if sum_abs > 1e-8:
            res[idx] = slice_x / sum_abs
        else:
            res[idx] = 0.0
    return res


def _if(condition, true_val, false_val):
    """
    IF 算子: 如果 condition > 0，返回 true_val，否则返回 false_val。
    支持向量输入。
    """
    cond = np.nan_to_num(condition, nan=0.0, posinf=0.0, neginf=0.0)
    return np.where(cond > 0, true_val, false_val)

def _signpow(x, p):
    """
    SignPow 算子: sign(x) * (abs(x) ** p)
    """
    x_clean = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
    p_clean = np.clip(np.nan_to_num(p, nan=1.0, posinf=1.0, neginf=1.0), -10.0, 10.0)
    res = np.sign(x_clean) * (np.abs(x_clean) ** p_clean)
    return np.clip(np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)

def make_ts_cov(window):
    """
    Ts_Cov: 过去 window 天的时间序列协方差
    """
    def _ts_cov(x, y):
        x = np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        y = np.clip(np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        sum_x = np.zeros_like(x); sum_y = np.zeros_like(y)
        sum_xy = np.zeros_like(x)
        
        for i in range(window):
            rx = np.roll(x, i)
            ry = np.roll(y, i)
            sum_x += rx
            sum_y += ry
            sum_xy += rx * ry
            
        mean_x = sum_x / window
        mean_y = sum_y / window
        cov = (sum_xy / window) - (mean_x * mean_y)
        
        res = np.clip(np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0), -1e10, 1e10)
        return DataContext.mask_invalid_ts(res, window, default_val=0.0)
    return _ts_cov


# ==============================================================================
# 注册到 gplearn 的算子库
# ==============================================================================
custom_operations = [
    # --- 单变量与横截面算子 ---
    make_function(function=_cs_rank, name='rank', arity=1),
    make_function(function=_cs_scale, name='scale', arity=1),
    make_function(function=_cs_zscore, name='cs_zscore', arity=1),
    make_function(function=_cs_mad, name='cs_mad', arity=1),
    make_function(function=_sign, name='sign', arity=1),
    
    # --- 基础算子 ---
    make_function(function=_if, name='if', arity=3),
    make_function(function=_signpow, name='signpow', arity=2),
]

# 动态批量注册所有需要的窗口大小
for w in [1, 2, 3, 5, 7, 10, 15, 20, 30]:
    custom_operations.extend([
        make_function(function=make_ts_mean(w), name=f'tsmean{w}', arity=1),
        make_function(function=make_ts_sum(w), name=f'tssum{w}', arity=1),
        make_function(function=make_ts_std(w), name=f'tsstd{w}', arity=1),
        make_function(function=make_ts_max(w), name=f'tsmax{w}', arity=1),
        make_function(function=make_ts_min(w), name=f'tsmin{w}', arity=1),
        make_function(function=make_ts_rank(w), name=f'tsrank{w}', arity=1),
        make_function(function=make_ts_argmax(w), name=f'tsargmax{w}', arity=1),
        make_function(function=make_ts_argmin(w), name=f'tsargmin{w}', arity=1),
        make_function(function=make_ts_delay(w), name=f'delay{w}', arity=1),
        make_function(function=make_ts_delta(w), name=f'delta{w}', arity=1),
        make_function(function=make_ts_corr(w), name=f'corr{w}', arity=2),
        make_function(function=make_ts_cov(w), name=f'cov{w}', arity=2),
        make_function(function=make_ts_decay_linear(w), name=f'decay{w}', arity=1),
    ])