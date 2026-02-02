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
    # Alpha #1: (-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))
    # Simplified: focus on volume-price relationship
    {
        "name": "Alpha#001_Simple",
        "formula": "mul(neg(tsrank10(volume)), tsrank10(div(sub(close, open), add(open, 0.001))))",
        "description": "Volume-price divergence signal"
    },
    
    # Alpha #2: (-1 * delta((((close - low) - (high - close)) / (high - low)), 1))
    # Position in daily range momentum
    {
        "name": "Alpha#002",
        "formula": "neg(delta1(div(sub(sub(sub(close, low), sub(high, close)), add(sub(high, low), 0.001)))))",
        "description": "Intraday position momentum"
    },
    
    # Alpha #3: sum(((close=delay(close,1))?0:close-(close>delay(close,1)?min(low,delay(close,1)):max(high,delay(close,1)))),6)
    # Simplified to momentum
    {
        "name": "Alpha#003_Simple",
        "formula": "tssum5(delta1(close))",
        "description": "Simple momentum sum"
    },
    
    # Alpha #4: ((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1 * 1) : ...)
    # Volatility breakout
    {
        "name": "Alpha#004_Simple",
        "formula": "sub(tsmean5(close), tsstd5(close))",
        "description": "Mean reversion with volatility"
    },
    
    # Alpha #6: (-1 * correlation(open, volume, 10))
    {
        "name": "Alpha#006",
        "formula": "neg(corr5(open, volume))",
        "description": "Open-volume negative correlation"
    },
    
    # Alpha #9: sma(((high+low)/2-(delay(high,1)+delay(low,1))/2)*(high-low)/volume,7,2)
    # Mid-price momentum weighted by liquidity
    {
        "name": "Alpha#009_Simple",
        "formula": "decay5(mul(delta1(div(add(high, low), 2.0)), div(sub(high, low), add(volume, 1.0))))",
        "description": "Mid-price momentum with volume weighting"
    },
    
    # Alpha #10: rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ...))
    # Trending momentum
    {
        "name": "Alpha#010_Simple",
        "formula": "rank(mul(delta1(close), if(tsmin5(delta1(close)), 1.0, neg(1.0))))",
        "description": "Conditional momentum based on trend"
    },
    
    # Alpha #12: (sign(delta(volume, 1)) * (-1 * delta(close, 1)))
    # Volume-price divergence
    {
        "name": "Alpha#012",
        "formula": "mul(delta1(volume), neg(delta1(close)))",
        "description": "Volume price divergence"
    },
    
    # Alpha #13: (-1 * rank(covariance(rank(close), rank(volume), 5)))
    {
        "name": "Alpha#013",
        "formula": "neg(rank(cov5(rank(close), rank(volume))))",
        "description": "Close-volume covariance ranking"
    },
    
    # Alpha #16: (-1 * rank(covariance(rank(high), rank(volume), 5)))
    {
        "name": "Alpha#016",
        "formula": "neg(rank(cov5(rank(high), rank(volume))))",
        "description": "High-volume covariance ranking"
    },
    
    # Alpha #17: (((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) * rank(ts_rank((volume / adv20), 5)))
    # Simplified - removing adv20
    {
        "name": "Alpha#017_Simple",
        "formula": "mul(mul(neg(rank(tsrank10(close))), rank(delta1(delta1(close)))), rank(tsrank5(volume)))",
        "description": "Multi-factor momentum combo"
    },
    
    # Alpha #18: (-1 * rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open, 10))))
    {
        "name": "Alpha#018_Simple",
        "formula": "neg(rank(add(tsstd5(abs(sub(close, open))), sub(close, open))))",
        "description": "Open-close volatility and deviation"
    },
    
    # Alpha #19: ((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns, 250)))))
    # Reversal signal - simplified
    {
        "name": "Alpha#019_Simple",
        "formula": "mul(neg(delta1(close)), rank(tssum20(delta1(close))))",
        "description": "Reversal with cumulative return"
    },
    
    # Alpha #20: (((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open - delay(low, 1))))
    {
        "name": "Alpha#020_Simple",
        "formula": "mul(neg(rank(sub(open, delay1(high)))), rank(sub(open, delay1(close))))",
        "description": "Gap analysis"
    },
    
    # Custom: Simple mean reversion
    {
        "name": "Mean_Reversion_5d",
        "formula": "neg(sub(close, tsmean5(close)))",
        "description": "5-day mean reversion"
    },
    
    # Custom: Volatility-adj momentum
    {
        "name": "Vol_Adj_Momentum",
        "formula": "div(tssum10(delta1(close)), add(tsstd10(close), 0.001))",
        "description": "Volatility-adjusted momentum"
    },
    
    # Custom: Price-volume correlation
    {
        "name": "Price_Volume_Corr",
        "formula": "corr5(close, volume)",
        "description": "5-day price-volume correlation"
    },
    
    # Custom: High-Low range
    {
        "name": "Range_Expansion",
        "formula": "sub(tsmax10(high), tsmin10(low))",
        "description": "10-day range expansion"
    },
    
    # Custom: Price position in range
    {
        "name": "Price_Position",
        "formula": "div(sub(close, tsmin20(low)), add(sub(tsmax20(high), tsmin20(low)), 0.001))",
        "description": "Price position in 20-day range"
    },
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
