"""
WorldQuant 101 Alpha Factors - Extended Library

本模块扩展了原有的20个WQ101因子，新增30+个经典因子，覆盖6大类别：
1. 动量反转类 (Momentum/Reversal)
2. 波动率类 (Volatility)
3. 成交量价格类 (Volume-Price)
4. 极值检测类 (Extremes)
5. 高阶统计类 (Higher-Order Statistics)
6. 截面关系类 (Cross-Sectional)

这些因子可用于：
- 直接回测评估
- GP算法的种子注入
- 因子组合优化
"""

# ========================================
# 动量反转类 (Momentum/Reversal) - 10个
# ========================================

WQ101_MOMENTUM_REVERSAL = [
    # Alpha #11: ((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3)))
    {
        "name": "Alpha#011_Simple",
        "formula": "mul(add(rank(tsmax3(sub(close, open))), rank(tsmin3(sub(close, open)))), rank(delta1(volume)))",
        "description": "VWAP偏离的动量信号",
        "category": "momentum"
    },
    
    # Alpha #12: (sign(delta(volume, 1)) * (-1 * delta(close, 1)))
    {
        "name": "Alpha#012",
        "formula": "mul(delta1(volume), neg(delta1(close)))",
        "description": "成交量-价格背离",
        "category": "reversal"
    },
    
    # Alpha #14: ((-1 * rank(delta(returns, 3))) * correlation(open, volume, 10))
    {
        "name": "Alpha#014_Simple",
        "formula": "mul(neg(rank(delta1(close))), corr5(open, volume))",
        "description": "收益率变化与开盘量价关系",
        "category": "momentum"
    },
    
    # Alpha #15: (-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))
    {
        "name": "Alpha#015_Simple",
        "formula": "neg(tssum5(rank(corr5(rank(high), rank(volume)))))",
        "description": "高点与成交量相关性累积",
        "category": "reversal"
    },
    
    # Alpha #21: (((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ...
    # Simplified to momentum breakout
    {
        "name": "Alpha#021_Breakout",
        "formula": "sub(tsmean7(close), tsstd10(close))",
        "description": "趋势突破信号",
        "category": "momentum"
    },
    
    # Alpha #30: (((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) + sign((delay(close, 2) - delay(close, 3)))))) * sum(volume, 5)) / sum(volume, 20))
    # Simplified
    {
        "name": "Alpha#030_Simple",
        "formula": "div(tssum5(volume), add(tssum20(volume), 1.0))",
        "description": "短期成交量占比",
        "category": "momentum"
    },
    
    # Alpha #41: (((high * low)^0.5) - vwap)
    {
        "name": "Alpha#041_Simple",
        "formula": "sub(mul(high, low), close)",
        "description": "几何均价偏离",
        "category": "reversal"
    },
    
    # Alpha #51: (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))
    # Simplified using available delays
    {
        "name": "Alpha#051_Simple",
        "formula": "sub(delay5(close), close)",
        "description": "10日动量衰减",
        "category": "momentum"
    },
    
    # Alpha #53: (-1 * delta((((close - low) - (high - close)) / (close - low)), 9))
    {
        "name": "Alpha#053_Simple",
        "formula": "neg(delta1(div(sub(sub(close, low), sub(high, close)), add(sub(close, low), 0.001))))",
        "description": "日内位置变化",
        "category": "reversal"
    },
    
    # Custom: ROC (Rate of Change)
    {
        "name": "ROC_5d",
        "formula": "div(sub(close, delay5(close)), add(delay5(close), 0.001))",
        "description": "5日变化率",
        "category": "momentum"
    },
]

# ========================================
# 波动率类 (Volatility) - 8个
# ========================================

WQ101_VOLATILITY = [
    # Alpha #22: (-1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))))
    {
        "name": "Alpha#022_Simple",
        "formula": "neg(mul(delta1(corr5(high, volume)), rank(tsstd20(close))))",
        "description": "高点-成交量相关性变化与波动率",
        "category": "volatility"
    },
    
    # Alpha #23: (((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)
    # Simplified
    {
        "name": "Alpha#023_Simple",
        "formula": "neg(mul(delta1(high), rank(sub(high, tsmean20(high)))))",
        "description": "高点突破波动",
        "category": "volatility"
    },
    
    # Alpha #24: ((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) ||
    #             ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1 * (close - ts_min(close, 100))) : (-1 * delta(close, 3)))
    # Highly simplified
    {
        "name": "Alpha#024_Simple",
        "formula": "neg(sub(close, tsmin20(close)))",
        "description": "相对低点距离",
        "category": "volatility"
    },
    
    # Alpha #33: rank((-1 * ((1 - (open / close))^1)))
    {
        "name": "Alpha#033",
        "formula": "rank(neg(sub(1.0, div(open, add(close, 0.001)))))",
        "description": "开盘缺口",
        "category": "volatility"
    },
    
    # Alpha #34: rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))
    # Simplified
    {
        "name": "Alpha#034_Simple",
        "formula": "add(rank(div(tsstd5(close), add(tsstd10(close), 0.001))), rank(delta1(close)))",
        "description": "波动率比率与价格变化",
        "category": "volatility"
    },
    
    # Custom: ATR-like (True Range)
    {
        "name": "True_Range",
        "formula": "sub(high, low)",
        "description": "日内波幅",
        "category": "volatility"
    },
    
    # Custom: Volatility Ratio
    {
        "name": "Vol_Ratio_5_20",
        "formula": "div(tsstd5(close), add(tsstd20(close), 0.001))",
        "description": "短期/长期波动率比",
        "category": "volatility"
    },
    
    # Custom: High-Low Range Rank
    {
        "name": "HL_Range_Rank",
        "formula": "rank(div(sub(high, low), add(close, 0.001)))",
        "description": "振幅排名",
        "category": "volatility"
    },
]

# ========================================
# 成交量价格类 (Volume-Price) - 10个
# ========================================

WQ101_VOLUME_PRICE = [
    # Alpha #25: rank(((((-1 * returns) * adv20) * vwap) * (high - close)))
    # Simplified (adv20 -> volume)
    {
        "name": "Alpha#025_Simple",
        "formula": "rank(mul(mul(neg(delta1(close)), volume), sub(high, close)))",
        "description": "下跌量价厚度",
        "category": "volume"
    },
    
    # Alpha #26: (-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))
    {
        "name": "Alpha#026",
        "formula": "neg(tsmax5(corr5(tsrank5(volume), tsrank5(high))))",
        "description": "量价排名相关性峰值",
        "category": "volume"
    },
    
    # Alpha #27: ((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1 * 1) : 1)
    # Simplified
    {
        "name": "Alpha#027_Simple",
        "formula": "rank(corr5(rank(volume), rank(close)))",
        "description": "成交量-价格排名相关",
        "category": "volume"
    },
    
    # Alpha #28: scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))
    # Simplified
    {
        "name": "Alpha#028_Simple",
        "formula": "scale(sub(div(add(high, low), 2.0), close))",
        "description": "中间价偏离标准化",
        "category": "volume"
    },
    
    # Alpha #37: (rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))
    # Simplified window
    {
        "name": "Alpha#037_Simple",
        "formula": "add(rank(corr5(delay1(sub(open, close)), close)), rank(sub(open, close)))",
        "description": "隔夜缺口持续性",
        "category": "volume"
    },
    
    # Custom: Volume Momentum
    {
        "name": "Volume_Momentum",
        "formula": "div(volume, add(tsmean20(volume), 1.0))",
        "description": "成交量相对强度",
        "category": "volume"
    },
    
    # Custom: Price-Volume Trend
    {
        "name": "PV_Trend",
        "formula": "mul(delta1(close), rank(volume))",
        "description": "价格变化与成交量排名",
        "category": "volume"
    },
    
    # Custom: Accumulation/Distribution
    {
        "name": "Accum_Dist",
        "formula": "mul(div(sub(sub(close, low), sub(high, close)), add(sub(high, low), 0.001)), volume)",
        "description": "累积/派发线",
        "category": "volume"
    },
    
    # Custom: Money Flow
    {
        "name": "Money_Flow",
        "formula": "mul(div(add(high, add(low, close)), 3.0), volume)",
        "description": "资金流",
        "category": "volume"
    },
    
    # Custom: Volume-Weighted Return
    {
        "name": "Vol_Weighted_Ret",
        "formula": "mul(delta1(close), tsrank10(volume))",
        "description": "成交量加权收益",
        "category": "volume"
    },
]

# ========================================
# 极值检测类 (Extremes) - 5个
# ========================================

WQ101_EXTREMES = [
    # Alpha #40: ((-1 * rank(stddev(high, 10))) * correlation(high, volume, 10))
    {
        "name": "Alpha#040",
        "formula": "mul(neg(rank(tsstd10(high))), corr5(high, volume))",
        "description": "高点波动率与量价相关",
        "category": "extremes"
    },
    
    # Alpha #50: (-1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))
    {
        "name": "Alpha#050",
        "formula": "neg(tsmax5(rank(corr5(rank(volume), rank(close)))))",
        "description": "量价排名相关性极值",
        "category": "extremes"
    },
    
    # Alpha #60: (0 - (1 * ((2 * scale(rank(((((close - low) - (high - close)) / (high - low)) * volume)))) - scale(rank(ts_argmax(close, 10))))))
    # Simplified
    {
        "name": "Alpha#060_Simple",
        "formula": "sub(scale(mul(div(sub(sub(close, low), sub(high, close)), add(sub(high, low), 0.001)), volume)), scale(rank(tsargmax5(close))))",
        "description": "位置加权成交量与极值位置",
        "category": "extremes"
    },
    
    # Custom: Distance from 20-day High
    {
        "name": "Dist_From_High",
        "formula": "div(sub(tsmax20(close), close), add(tsmax20(close), 0.001))",
        "description": "距20日高点距离",
        "category": "extremes"
    },
    
    # Custom: Distance from 20-day Low
    {
        "name": "Dist_From_Low",
        "formula": "div(sub(close, tsmin20(close)), add(close, 0.001))",
        "description": "距20日低点距离",
        "category": "extremes"
    },
]

# ========================================
# 高阶统计类 (Higher-Order Statistics) - 5个
# ========================================

WQ101_HIGHER_ORDER = [
    # Custom: Return Skewness
    {
        "name": "Return_Skewness_5d",
        "formula": "ts_skewness_5(delta1(close))",
        "description": "5日收益率偏度",
        "category": "higher_order",
        "note": "需要调用已有的 ts_skewness_5 算子"
    },
    
    # Custom: Return Kurtosis
    {
        "name": "Return_Kurtosis_5d",
        "formula": "ts_kurtosis_5(delta1(close))",
        "description": "5日收益率峰度",
        "category": "higher_order",
        "note": "需要调用已有的 ts_kurtosis_5 算子"
    },
    
    # Custom: Volume Skewness
    {
        "name": "Volume_Skewness",
        "formula": "ts_skewness_5(volume)",
        "description": "成交量偏度",
        "category": "higher_order"
    },
    
    # Custom: MAD (Median Absolute Deviation)
    {
        "name": "Return_MAD",
        "formula": "ts_mad_5(delta1(close))",
        "description": "收益率中位绝对偏差",
        "category": "higher_order",
        "note": "稳健波动率指标"
    },
    
    # Custom: Co-Skewness (简化为价量偏度乘积)
    {
        "name": "Price_Volume_Skew",
        "formula": "mul(ts_skewness_5(close), ts_skewness_5(volume))",
        "description": "价格-成交量联合偏度",
        "category": "higher_order"
    },
]

# ========================================
# 截面关系类 (Cross-Sectional) - 7个
# ========================================

WQ101_CROSS_SECTIONAL = [
    # Alpha #43: (ts_rank((volume / adv20), 20) * ts_rank((-1 * delta(close, 7)), 8))
    # Simplified
    {
        "name": "Alpha#043_Simple",
        "formula": "mul(tsrank20(div(volume, add(tsmean20(volume), 1.0))), tsrank10(neg(delta1(close))))",
        "description": "成交量相对强度与反转",
        "category": "cross_sectional"
    },
    
    # Alpha #48: indneutralize(((correlation(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1)) / close), IndClass.subindustry) / sum(((delta(close, 1) / delay(close, 1))^2), 250))
    # Highly simplified
    {
        "name": "Alpha#048_Simple",
        "formula": "div(mul(corr5(delta1(close), delay1(delta1(close))), delta1(close)), add(close, 0.001))",
        "description": "自相关加权收益",
        "category": "cross_sectional"
    },
    
    # Alpha #62: ((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) + rank(open)) < (rank(((high + low) / 2)) + rank(high))))) * -1)
    # Simplified
    {
        "name": "Alpha#062_Simple",
        "formula": "neg(rank(sub(rank(open), rank(div(add(high, low), 2.0)))))",
        "description": "开盘价与中间价排名差",
        "category": "cross_sectional"
    },
    
    # Custom: Relative Strength (vs mean)
    {
        "name": "Relative_Strength",
        "formula": "rank(sub(close, tsmean20(close)))",
        "description": "相对强度排名",
        "category": "cross_sectional"
    },
    
    # Custom: Cross-sectional Momentum
    {
        "name": "CS_Momentum",
        "formula": "rank(div(sub(close, delay5(close)), add(delay5(close), 0.001)))",
        "description": "截面动量排名",
        "category": "cross_sectional"
    },
    
    # Custom: Liquidity Rank
    {
        "name": "Liquidity_Rank",
        "formula": "rank(div(volume, add(tsstd20(volume), 1.0)))",
        "description": "流动性稳定性排名",
        "category": "cross_sectional"
    },
    
    # Custom: Composite Rank
    {
        "name": "Composite_Rank",
        "formula": "add(add(rank(delta1(close)), rank(volume)), rank(sub(close, open)))",
        "description": "综合排名因子",
        "category": "cross_sectional"
    },
]

# ========================================
# 汇总所有扩展因子
# ========================================

WQ101_EXTENDED_ALPHAS = (
    WQ101_MOMENTUM_REVERSAL +
    WQ101_VOLATILITY +
    WQ101_VOLUME_PRICE +
    WQ101_EXTREMES +
    WQ101_HIGHER_ORDER +
    WQ101_CROSS_SECTIONAL
)

def get_extended_alpha_count():
    """返回扩展因子库数量"""
    return len(WQ101_EXTENDED_ALPHAS)

def get_extended_alphas_by_category(category):
    """根据类别筛选因子"""
    return [alpha for alpha in WQ101_EXTENDED_ALPHAS if alpha.get("category") == category]

def get_all_categories():
    """获取所有因子类别"""
    return list(set(alpha.get("category") for alpha in WQ101_EXTENDED_ALPHAS))

def print_summary():
    """打印因子库概览"""
    print(f"WQ101 Extended Factor Library")
    print(f"=" * 50)
    print(f"Total Factors: {get_extended_alpha_count()}")
    print(f"\nBreakdown by Category:")
    for cat in get_all_categories():
        count = len(get_extended_alphas_by_category(cat))
        print(f"  - {cat.capitalize()}: {count} factors")
    print(f"=" * 50)

if __name__ == "__main__":
    print_summary()
    print("\n示例因子:")
    for i, alpha in enumerate(WQ101_EXTENDED_ALPHAS[:5]):
        print(f"{i+1}. {alpha['name']}: {alpha['description']}")
