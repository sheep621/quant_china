import numpy as np
import pandas as pd
from gplearn.functions import make_function

# --------------------------
# 1. Basic Element-wise Ops
# --------------------------

def _protected_div(x1, x2):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(np.abs(x2) > 0.001, np.divide(x1, x2), 1.)

def _protected_log(x1):
    with np.errstate(invalid='ignore'):
        return np.where(x1 > 0.001, np.log(x1), 0.)
        
def _protected_sqrt(x1):
    with np.errstate(invalid='ignore'):
        return np.where(x1 > 0., np.sqrt(x1), 0.)

def _signed_power(x1, x2):
    """ x1 ^ x2 with sign preservation """
    with np.errstate(invalid='ignore'):
        return np.sign(x1) * (np.abs(x1) ** x2)

# --------------------------
# 2. Time-Series Ops (Simulation)
# --------------------------
# Note: True TS ops in gplearn on flat arrays are tricky.
# We implemented "simulated" lags by assuming the data stream is fed in order OR
# by pre-calculating features.
# For this 'Alpha Factory' demo, we will expose simple "shift" logic that relies on
# the input data being strictly time-sorted (which our Cleaner ensures).
# WARN: This is risky if batch shuffling happens (like in standard ML), but ok for sequential Genetic Programming.

def _ts_delay_1(x1): return np.roll(x1, 1)
def _ts_delay_5(x1): return np.roll(x1, 5)

def _ts_delta_1(x1): return x1 - np.roll(x1, 1)

# --------------------------
# 3. Cross-Sectional Ops (Simulation)
# --------------------------
# Without Day/Stock index, we can't do exact cross-sectional rank.
# BUT, if we assume the input X contains ALL stocks for ONE day (or large batches),
# we can approximate rank.
# Better yet: In `AlphaGenerator`, we can group by date before passing to function?
# No, gplearn passes column vectors.

# Compromise: We implement `rank` which ranks the ENTIRE batch.
# If the batch is one day -> Perfect.
# If the batch is multi-day -> It ranks across time and space (Global Rank), which is also a valid alpha type.

def _rank(x1):
    """Percentile rank of the input vector"""
    # Use pandas for robust ranking handling NaN
    return pd.Series(x1).rank(pct=True).fillna(0.5).values

def _scale(x1):
    """Scale to sum(abs(x)) = 1 (or close to it)"""
    s = np.nansum(np.abs(x1))
    return x1 / (s + 0.0001)

# --------------------------
# 4. A-Share Specific Ops
# --------------------------

def _limit_dist_up(close):
    """Distance to 10% limit up approx"""
    # Assuming close is roughly normalized or we know pre-close
    # This operator is hard without pre-close.
    # Let's skip for pure flat array GP unless we pass pre-close as feature
    return close

# --------------------------
# Registration
# --------------------------

protected_div = make_function(function=_protected_div, name='div', arity=2)
protected_log = make_function(function=_protected_log, name='log', arity=1)
protected_sqrt = make_function(function=_protected_sqrt, name='sqrt', arity=1)
signed_power = make_function(function=_signed_power, name='signed_pow', arity=2)

ts_delay_1 = make_function(function=_ts_delay_1, name='delay1', arity=1)
ts_delta_1 = make_function(function=_ts_delta_1, name='delta1', arity=1)

rank = make_function(function=_rank, name='rank', arity=1)
scale = make_function(function=_scale, name='scale', arity=1)

custom_operations = [
    protected_div, protected_log, protected_sqrt, signed_power,
    ts_delay_1, ts_delta_1,
    rank, scale
]
