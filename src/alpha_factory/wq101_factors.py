"""
WorldQuant 101 Alpha Factors (Simplified Versions)

This module contains simplified implementations of some classic WQ101 factors.
These can be used directly for backtesting or as "seed formulas" for GP evolution.

Note: Some factors have been simplified to work with the available operators.
Complex factors requiring special data (like industry classifications, ADV20, etc.)
are either simplified or omitted.
"""

# WQ101 Alpha Factors (Partial List - Simplified)
# Format: {"name": "Alpha#XXX", "formula": "expression", "description": "..."}

WQ101_ALPHAS = [
    # --- Classic Alphas (Mapped to supported operators) ---
    {"name": "Alpha#001_Simple", "formula": "mul(neg(tsrank10(volume)), tsrank10(div(sub(close, open), add(open, 0.001))))", "description": "Volume-price divergence signal"},
    {"name": "Alpha#002", "formula": "neg(delta1(div(sub(sub(sub(close, low), sub(high, close)), add(sub(high, low), 0.001)))))", "description": "Intraday position momentum"},
    {"name": "Alpha#003_Simple", "formula": "tssum5(delta1(close))", "description": "Simple momentum sum"},
    {"name": "Alpha#004_Simple", "formula": "sub(tsmean5(close), tsstd5(close))", "description": "Mean reversion with volatility"},
    {"name": "Alpha#005_Simple", "formula": "rank(sub(open, mul(tsmean10(volume), 1.0)))", "description": "Open vs Moving Average Volume rank"},
    {"name": "Alpha#006", "formula": "neg(corr5(open, volume))", "description": "Open-volume negative correlation"},
    {"name": "Alpha#007_Simple", "formula": "if(sub(tsmean20(volume), volume), mul(neg(1), tsrank20(abs(delta1(close)))), rank(delta1(close)))", "description": "Conditional momentum based on volume"},
    {"name": "Alpha#008_Simple", "formula": "neg(rank(mul(sub(tsmean10(open), tsmean10(close)), 1.0)))", "description": "Trend ranking"},
    {"name": "Alpha#009_Simple", "formula": "decay5(mul(delta1(div(add(high, low), 2.0)), div(sub(high, low), add(volume, 1.0))))", "description": "Mid-price momentum with volume weighting"},
    {"name": "Alpha#010_Simple", "formula": "rank(mul(delta1(close), if(tsmin5(delta1(close)), 1.0, neg(1.0))))", "description": "Conditional momentum based on trend"},
    {"name": "Alpha#011_Simple", "formula": "mul(rank(tsmax5(sub(tsmax5(high), close))), rank(tsmin5(sub(close, tsmin5(low)))))", "description": "Channel breakout rank"},
    {"name": "Alpha#012", "formula": "mul(delta1(volume), neg(delta1(close)))", "description": "Volume price divergence"},
    {"name": "Alpha#013", "formula": "neg(rank(cov5(rank(close), rank(volume))))", "description": "Close-volume covariance ranking"},
    {"name": "Alpha#014_Simple", "formula": "neg(rank(delta1(close)))", "description": "Short term mean reversion"},
    {"name": "Alpha#015_Simple", "formula": "mul(neg(rank(corr5(high, volume))), rank(corr5(close, volume)))", "description": "Price-Volume Correlation divergence"},
    {"name": "Alpha#016", "formula": "neg(rank(cov5(rank(high), rank(volume))))", "description": "High-volume covariance ranking"},
    {"name": "Alpha#017_Simple", "formula": "mul(mul(neg(rank(tsrank10(close))), rank(delta1(delta1(close)))), rank(tsrank5(volume)))", "description": "Multi-factor momentum combo"},
    {"name": "Alpha#018_Simple", "formula": "neg(rank(add(tsstd5(abs(sub(close, open))), sub(close, open))))", "description": "Open-close volatility and deviation"},
    {"name": "Alpha#019_Simple", "formula": "mul(neg(delta1(close)), rank(tssum20(delta1(close))))", "description": "Reversal with cumulative return"},
    {"name": "Alpha#020_Simple", "formula": "mul(neg(rank(sub(open, delay1(high)))), rank(sub(open, delay1(close))))", "description": "Gap analysis"},
    {"name": "Alpha#021_Simple", "formula": "if(sub(tsmean10(close), close), neg(1.0), 1.0)", "description": "Simple moving average crossover"},
    {"name": "Alpha#022_Simple", "formula": "mul(neg(delta1(corr5(high, volume))), rank(tsstd5(close)))", "description": "Volatility adjusted correlation change"},
    {"name": "Alpha#023_Simple", "formula": "if(tsmean20(high), mul(neg(delta1(high)), 1.0), 0.0)", "description": "Conditional high reversal"},
    {"name": "Alpha#024_Simple", "formula": "if(sub(delta1(tsmean20(close)), 0.0), rank(close), neg(rank(close)))", "description": "Trend conditional rank"},
    {"name": "Alpha#025_Simple", "formula": "mul(rank(mul(neg(delta1(close)), 1.0)), rank(mul(neg(delta1(volume)), 1.0)))", "description": "Short term price volume reversal"},
    {"name": "Alpha#026_Simple", "formula": "neg(tsmax5(corr5(tsrank5(volume), tsrank5(high))))", "description": "Max volume high rank correlation"},
    {"name": "Alpha#027_Simple", "formula": "if(rank(tsmean10(volume)), rank(sub(close, tsmean10(close))), 0.0)", "description": "Volume conditional trend"},
    {"name": "Alpha#028_Simple", "formula": "scale(sub(corr5(tsmean20(volume), low), 0.0))", "description": "Scaled correlation of volume avg and low"},
    {"name": "Alpha#029_Simple", "formula": "tsmin5(rank(add(rank(delta1(close)), rank(delta1(volume)))))", "description": "Min rank of price volume delta sum"},
    {"name": "Alpha#030_Simple", "formula": "mul(rank(signpow(delta1(close), 2.0)), neg(1.0))", "description": "Signed quadratic mean reversion"},
    {"name": "Alpha#031_Simple", "formula": "rank(sub(rank(rank(decay10(rank(rank(delta1(close)))))), 0.0))", "description": "Deep decay ranking"},
    {"name": "Alpha#032_Simple", "formula": "scale(mul(tsmean10(close), tsmean10(volume)))", "description": "Scaled Price Volume Trend"},
    {"name": "Alpha#033_Simple", "formula": "rank(mul(neg(1), sub(open, close)))", "description": "Intraday reversal rank"},
    {"name": "Alpha#034_Simple", "formula": "rank(div(sub(tsstd5(close), tsstd10(close)), add(tsstd20(close), 0.001)))", "description": "Volatility term structure"},
    {"name": "Alpha#035_Simple", "formula": "mul(tsrank10(volume), rank(sub(close, delay1(high))))", "description": "Volume weighted high breakout"},
    {"name": "Alpha#036_Simple", "formula": "sub(rank(corr5(close, volume)), rank(corr5(tsmean10(close), tsmean10(volume))))", "description": "Correlation difference"},
    {"name": "Alpha#037_Simple", "formula": "rank(sub(corr5(delay1(open), delay1(close)), 0.0))", "description": "Previous day intraday correlation"},
    {"name": "Alpha#038_Simple", "formula": "mul(neg(1), rank(tsrank10(close)))", "description": "Simple reversal of time rank"},
    {"name": "Alpha#039_Simple", "formula": "neg(rank(sub(delay1(close), delay5(close))))", "description": "5-day momentum reversal"},
    {"name": "Alpha#040_Simple", "formula": "mul(neg(1), rank(tsstd10(high)))", "description": "Short high volatility"},
    {"name": "Alpha#041_Simple", "formula": "mul(decay5(delta1(high)), decay5(delta1(volume)))", "description": "Decayed momentum cross"},
    {"name": "Alpha#042_Simple", "formula": "rank(sub(tsmean10(high), tsmean10(low)))", "description": "True range momentum"},
    {"name": "Alpha#043_Simple", "formula": "tsrank20(div(volume, add(tsmean20(volume), 1.0)))", "description": "Relative volume jump"},
    {"name": "Alpha#044_Simple", "formula": "neg(corr5(high, rank(volume)))", "description": "High and rank volume correlation"},
    {"name": "Alpha#045_Simple", "formula": "mul(rank(sub(tsmean5(close), close)), rank(sub(tsmean20(volume), volume)))", "description": "Mean reversion times volume drop"},
    {"name": "Alpha#046_Simple", "formula": "if(sub(close, delay1(close)), rank(sub(close, delay1(close))), 0.0)", "description": "Conditional absolute momentum"},
    {"name": "Alpha#047_Simple", "formula": "rank(div(tsmax5(high), add(tsmax20(high), 0.001)))", "description": "High local vs global"},
    {"name": "Alpha#049_Simple", "formula": "if(sub(delay1(close), 0.0), sub(close, delay1(close)), 0.0)", "description": "Valid return check"},
    {"name": "Alpha#050_Simple", "formula": "mul(neg(1), tsmax5(rank(corr5(rank(volume), rank(close)))))", "description": "Max ranking correlation reversal"},
    {"name": "Alpha#051_Simple", "formula": "if(sub(tsmean20(close), tsmean5(close)), 1.0, neg(1.0))", "description": "Moving average cross logic"},
    {"name": "Alpha#052_Simple", "formula": "rank(sub(tsmean20(volume), tsmin20(volume)))", "description": "Volume expansion rank"},
    {"name": "Alpha#053_Simple", "formula": "mul(neg(1), rank(sub(close, tsmin10(close))))", "description": "Low breakout reversal"},
    {"name": "Alpha#054_Simple", "formula": "neg(rank(sub(open, close)))", "description": "Intraday momentum"},
    {"name": "Alpha#055_Simple", "formula": "rank(sub(tsmean20(close), tsmean10(close)))", "description": "Medium term trend cross"},
    {"name": "Alpha#057_Simple", "formula": "neg(rank(sub(close, tsmean30(close))))", "description": "Longer term mean reversion"},
    {"name": "Alpha#060_Simple", "formula": "sub(rank(mul(2, close)), rank(add(high, low)))", "description": "Close relative to high/low"},
    {"name": "Alpha#061_Simple", "formula": "rank(div(tsmean5(volume), add(tsmean20(volume), 1.0)))", "description": "Volume moving average ratio"},
    {"name": "Alpha#062_Simple", "formula": "rank(sub(rank(corr5(low, tsmean20(volume))), 0.0))", "description": "Low vs long volume correlation"},
    {"name": "Alpha#064_Simple", "formula": "mul(neg(rank(corr5(open, volume))), rank(corr5(close, volume)))", "description": "Open vs Close volume correlation product"},
    {"name": "Alpha#065_Simple", "formula": "rank(div(tsmean10(volume), add(tsmean30(volume), 1.0)))", "description": "Volume trend expansion"},
    {"name": "Alpha#066_Simple", "formula": "sub(rank(decay5(delta1(close))), rank(decay10(delta1(close))))", "description": "Fast vs slow decayed momentum"},
    {"name": "Alpha#068_Simple", "formula": "mul(neg(1), rank(sub(delay1(high), delay1(close))))", "description": "Previous day top wick reversal"},
    {"name": "Alpha#071_Simple", "formula": "tsrank20(tsmean20(close))", "description": "Time rank of moving average"},
    {"name": "Alpha#073_Simple", "formula": "rank(sub(decay5(delta1(open)), decay5(delta1(close))))", "description": "Decayed intraday drop"},
    {"name": "Alpha#074_Simple", "formula": "rank(sub(corr5(close, tsmean20(volume)), 0.0))", "description": "Close vs long volume correlation rank"},
    {"name": "Alpha#075_Simple", "formula": "if(sub(close, low), rank(div(sub(high, close), add(sub(close, low), 0.001))), 0.0)", "description": "Intraday buying pressure"},
    {"name": "Alpha#078_Simple", "formula": "rank(sub(tsmean5(volume), tsmean10(volume)))", "description": "Volume momentum"},
    {"name": "Alpha#081_Simple", "formula": "rank(mul(log(add(volume, 1.0)), log(add(close, 1.0))))", "description": "Log price volume product"},
    {"name": "Alpha#083_Simple", "formula": "rank(div(sub(delay1(high), delay1(low)), add(tsmean5(volume), 1.0)))", "description": "Previous day range per volume"},
    {"name": "Alpha#084_Simple", "formula": "rank(sub(tsrank10(close), tsrank5(close)))", "description": "Time rank cross"},
    {"name": "Alpha#085_Simple", "formula": "rank(sub(corr5(high, tsmean20(volume)), 0.0))", "description": "High vs volume avg correlation"},
    {"name": "Alpha#086_Simple", "formula": "rank(sub(tsmean20(close), delay5(close)))", "description": "Moving average vs delayed"},
    {"name": "Alpha#088_Simple", "formula": "min(rank(decay5(rank(open))), rank(decay5(rank(close))))", "description": "Min decayed rank"},
    {"name": "Alpha#094_Simple", "formula": "rank(sub(tsrank10(volume), tsrank5(volume)))", "description": "Volume time rank momentum"},
    {"name": "Alpha#096_Simple", "formula": "rank(tsmax5(rank(corr5(tsmean5(volume), close))))", "description": "Rank of max correlation"},
    {"name": "Alpha#098_Simple", "formula": "rank(sub(decay5(corr5(tsmean20(volume), close)), 0.0))", "description": "Decayed correlation"},
    {"name": "Alpha#099_Simple", "formula": "if(sub(close, tsmin10(close)), rank(div(sub(tsmax10(high), close), add(sub(close, tsmin10(close)), 0.001))), 0.0)", "description": "Trend ratio ranking"},
    {"name": "Alpha#101_Simple", "formula": "div(sub(close, open), add(sub(high, low), 0.001))", "description": "Intraday return over range"},
    
    # --- Custom Robust Factor Additions ---
    {"name": "Mean_Reversion_5d", "formula": "neg(sub(close, tsmean5(close)))", "description": "5-day mean reversion"},
    {"name": "Vol_Adj_Momentum", "formula": "div(tssum10(delta1(close)), add(tsstd10(close), 0.001))", "description": "Volatility-adjusted momentum"},
    {"name": "Price_Volume_Corr", "formula": "corr5(close, volume)", "description": "5-day price-volume correlation"},
    {"name": "Range_Expansion", "formula": "sub(tsmax10(high), tsmin10(low))", "description": "10-day range expansion"},
    {"name": "Price_Position", "formula": "div(sub(close, tsmin20(low)), add(sub(tsmax20(high), tsmin20(low)), 0.001))", "description": "Price position in 20-day range"},
]

def get_alpha_count():
    """返回内置因子数量"""
    return len(WQ101_ALPHAS)

def get_alpha_names():
    """返回所有因子名称列表"""
    return [alpha["name"] for alpha in WQ101_ALPHAS]

def get_alpha_by_name(name):
    """根据名称获取因子"""
    for alpha in WQ101_ALPHAS:
        if alpha["name"] == name:
            return alpha
    return None
