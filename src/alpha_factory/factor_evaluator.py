"""
Factor Evaluator - 因子质量评估体系

本模块提供多维度的因子质量评估功能，包括：
1. 信息系数 (IC/ICIR)
2. 分组回测收益
3. 因子稳定性
4. 因子特异性 (与已有因子的正交性)

参考文献:
- WorldQuant Alpha 101
- 《量化投资：以Python为工具》第9章
- Barra Risk Model
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class FactorMetrics:
    """因子评估指标容器"""
    def __init__(self, **kwargs):
        self.IC_mean = kwargs.get('IC_mean', 0.0)
        self.IC_std = kwargs.get('IC_std', 0.0)
        self.ICIR = kwargs.get('ICIR', 0.0)
        self.IC_positive_ratio = kwargs.get('IC_positive_ratio', 0.0)
        
        self.group_1_ret = kwargs.get('group_1_ret', 0.0)
        self.group_5_ret = kwargs.get('group_5_ret', 0.0)
        self.long_short_ret = kwargs.get('long_short_ret', 0.0)
        self.long_short_sharpe = kwargs.get('long_short_sharpe', 0.0)
        
        self.IC_decay_rate = kwargs.get('IC_decay_rate', 0.0)
        self.turnover = kwargs.get('turnover', 0.0)
        
        self.factor_uniqueness = kwargs.get('factor_uniqueness', 1.0)
        
    def __repr__(self):
        return (f"FactorMetrics(ICIR={self.ICIR:.3f}, IC_mean={self.IC_mean:.4f}, "
                f"LongShort_Sharpe={self.long_short_sharpe:.2f}, Uniqueness={self.factor_uniqueness:.2f})")
    
    def to_dict(self):
        return self.__dict__
        
    def passes_quality_gate(self):
        """
        质量门控检查
        返回 (通过, 原因)
        """
        criteria = {
            'ICIR': (self.ICIR > 0.5, f"ICIR={self.ICIR:.3f} < 0.5"),
            'IC_positive_ratio': (self.IC_positive_ratio > 0.55, f"IC胜率={self.IC_positive_ratio:.2%} < 55%"),
            'turnover': (self.turnover < 0.5, f"换手率={self.turnover:.2%} > 50%"),
            'uniqueness': (self.factor_uniqueness > 0.3, f"特异性={self.factor_uniqueness:.2f} < 0.3"),
        }
        
        failed = [reason for passed, reason in criteria.values() if not passed]
        
        if not failed:
            return True, "所有质量检查通过"
        else:
            return False, "; ".join(failed)


class FactorEvaluator:
    """
    因子质量评估器
    """
    def __init__(self):
        pass
        
    def evaluate(self, factor_values, returns, dates=None, existing_factors=None):
        """
        完整的因子评估
        
        参数:
            factor_values: pd.Series or np.ndarray - 因子值
            returns: pd.Series or np.ndarray - 对应的未来收益率
            dates: pd.Series - 日期序列 (可选，用于时序分析)
            existing_factors: pd.DataFrame - 已有因子池 (用于计算特异性)
            
        返回:
            FactorMetrics
        """
        # 转换为Series便于计算
        if isinstance(factor_values, np.ndarray):
            factor_values = pd.Series(factor_values)
        if isinstance(returns, np.ndarray):
            returns = pd.Series(returns)
            
        # 去除NaN
        valid_mask = factor_values.notna() & returns.notna()
        factor_clean = factor_values[valid_mask]
        returns_clean = returns[valid_mask]
        
        if len(factor_clean) < 50:
            logger.warning(f"样本量过少 ({len(factor_clean)}), 评估不可靠")
            return FactorMetrics()
        
        # 1. IC指标
        ic_metrics = self._calculate_ic_metrics(factor_clean, returns_clean, dates)
        
        # 2. 分组回测
        group_metrics = self._calculate_group_returns(factor_clean, returns_clean)
        
        # 3. 稳定性指标
        stability_metrics = self._calculate_stability(factor_clean, returns_clean, dates)
        
        # 4. 特异性
        uniqueness = self._calculate_uniqueness(factor_clean, existing_factors)
        
        # 合并所有指标
        all_metrics = {**ic_metrics, **group_metrics, **stability_metrics, 'factor_uniqueness': uniqueness}
        
        return FactorMetrics(**all_metrics)
    
    def _calculate_ic_metrics(self, factor, returns, dates=None):
        """
        计算IC相关指标
        """
        # Spearman Rank IC (更稳健)
        try:
            ic, _ = spearmanr(factor, returns)
        except:
            ic = 0.0
            
        # 如果有日期，计算时序IC均值和标准差
        if dates is not None and len(dates) == len(factor):
            # 按日期分组计算IC
            df = pd.DataFrame({'factor': factor, 'returns': returns, 'date': dates})
            daily_ic = df.groupby('date').apply(
                lambda x: spearmanr(x['factor'], x['returns'])[0] if len(x) > 10 else np.nan
            )
            daily_ic = daily_ic.dropna()
            
            ic_mean = daily_ic.mean()
            ic_std = daily_ic.std()
            ic_positive_ratio = (daily_ic > 0).sum() / len(daily_ic) if len(daily_ic) > 0 else 0.0
        else:
            # 无时序信息，使用全样本IC
            ic_mean = ic
            ic_std = 0.0
            ic_positive_ratio = 1.0 if ic > 0 else 0.0
        
        # ICIR = IC_mean / IC_std
        icir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        return {
            'IC_mean': ic_mean,
            'IC_std': ic_std,
            'ICIR': icir,
            'IC_positive_ratio': ic_positive_ratio
        }
    
    def _calculate_group_returns(self, factor, returns, n_groups=5):
        """
        分组回测：将因子值分为n组，计算各组平均收益
        """
        df = pd.DataFrame({'factor': factor, 'returns': returns})
        
        # 按因子值分组 (1=最低, n=最高)
        df['group'] = pd.qcut(df['factor'], q=n_groups, labels=False, duplicates='drop') + 1
        
        # 计算各组平均收益
        group_rets = df.groupby('group')['returns'].mean()
        
        if len(group_rets) < 2:
            return {
                'group_1_ret': 0.0,
                'group_5_ret': 0.0,
                'long_short_ret': 0.0,
                'long_short_sharpe': 0.0
            }
        
        # 多空组合：做多最高组，做空最低组
        group_1_ret = group_rets.iloc[0] if len(group_rets) >= 1 else 0.0  # 最低组
        group_5_ret = group_rets.iloc[-1] if len(group_rets) >= n_groups else 0.0  # 最高组
        long_short_ret = group_5_ret - group_1_ret
        
        # 计算多空组合的Sharpe (简化版)
        # 理想情况下应该用时序收益率序列计算，这里用单次收益估计
        # Sharpe ~  E[R] / Std[R], 假设日度Sharpe
        df['long_short'] = df['returns'] * (df['group'] == df['group'].max()).astype(float) - \
                           df['returns'] * (df['group'] == df['group'].min()).astype(float)
        
        ls_mean = df['long_short'].mean()
        ls_std = df['long_short'].std()
        long_short_sharpe = (ls_mean / ls_std * np.sqrt(252)) if ls_std > 0 else 0.0
        
        return {
            'group_1_ret': group_1_ret,
            'group_5_ret': group_5_ret,
            'long_short_ret': long_short_ret,
            'long_short_sharpe': long_short_sharpe
        }
    
    def _calculate_stability(self, factor, returns, dates=None):
        """
        计算因子稳定性：
        - IC衰减率 (未来N天IC的衰减)
        - 换手率 (因子值变化导致的持仓调整)
        """
        # IC衰减率：简化计算，这里需要时序数据
        # 如果没有dates，无法计算衰减
        ic_decay_rate = 0.0
        
        # 换手率：因子排名变化
        # 简化：计算因子值的自相关性，1-自相关 ~ 换手率
        if len(factor) > 1:
            factor_lag = factor.shift(1)
            valid = factor.notna() & factor_lag.notna()
            if valid.sum() > 10:
                turnover_corr = factor[valid].corr(factor_lag[valid])
                turnover = 1 - turnover_corr if not np.isnan(turnover_corr) else 0.5
            else:
                turnover = 0.5  # 默认
        else:
            turnover = 0.5
        
        return {
            'IC_decay_rate': ic_decay_rate,
            'turnover': turnover
        }
    
    def _calculate_uniqueness(self, factor, existing_factors):
        """
        计算因子特异性：1 - max(corr(新因子, 已有因子))
        """
        if existing_factors is None or existing_factors.empty:
            return 1.0  #  完全独特
        
        # 计算与所有已有因子的相关性
        correlations = []
        for col in existing_factors.columns:
            existing = existing_factors[col]
            # 对齐索引
            common_idx = factor.index.intersection(existing.index)
            if len(common_idx) > 10:
                corr = factor.loc[common_idx].corr(existing.loc[common_idx])
                if not np.isnan(corr):
                    correlations.append(abs(corr))
        
        if not correlations:
            return 1.0
        
        max_corr = max(correlations)
        uniqueness = 1.0 - max_corr
        
        return uniqueness


def batch_evaluate_factors(factors_dict, returns, dates=None, existing_factors=None):
    """
    批量评估多个因子
    
    参数:
        factors_dict: dict {factor_name: factor_values}
        returns: pd.Series - 收益率
        dates: pd.Series - 日期
        existing_factors: pd.DataFrame - 已有因子池
        
    返回:
        pd.DataFrame - 评估结果汇总表
    """
    evaluator = FactorEvaluator()
    results = []
    
    for name, factor_values in factors_dict.items():
        logger.info(f"评估因子: {name}")
        metrics = evaluator.evaluate(factor_values, returns, dates, existing_factors)
        
        result = {'factor_name': name}
        result.update(metrics.to_dict())
        
        passed, reason = metrics.passes_quality_gate()
        result['pass_quality_gate'] = passed
        result['rejection_reason'] = reason if not passed else ''
        
        results.append(result)
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('ICIR', ascending=False)
    
    return df_results


# 示例使用
if __name__ == "__main__":
    # 生成模拟数据
    np.random.seed(42)
    n = 1000
    
    # 模拟因子：有一定预测能力
    factor_good = np.random.randn(n)
    returns = 0.05 * factor_good + np.random.randn(n) * 0.1  # 因子有信号
    
    # 模拟噪音因子
    factor_noise = np.random.randn(n)
    
    # 评估
    evaluator = FactorEvaluator()
    
    print("=" * 60)
    print("因子质量评估示例")
    print("=" * 60)
    
    metrics_good = evaluator.evaluate(pd.Series(factor_good), pd.Series(returns))
    print(f"\n优质因子评估结果:")
    print(metrics_good)
    passed, reason = metrics_good.passes_quality_gate()
    print(f"质量门控: {'✓ 通过' if passed else '✗ 未通过'} - {reason}")
    
    metrics_noise = evaluator.evaluate(pd.Series(factor_noise), pd.Series(returns))
    print(f"\n噪音因子评估结果:")
    print(metrics_noise)
    passed, reason = metrics_noise.passes_quality_gate()
    print(f"质量门控: {'✓ 通过' if passed else '✗ 未通过'} - {reason}")
    
    print("\n" + "=" * 60)
