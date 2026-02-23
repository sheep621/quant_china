"""
Factor Orthogonalizer - 因子正交化工具

提供两种正交化策略：
1. Löwdin 对称正交化 - 保持信息的同时去相关
2. 增量去重 - 高效的在线去重机制

参考：
- Löwdin, P. O. (1950). On the non-orthogonality problem
- Schmidt Orthogonalization
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class Orthogonalizer:
    """
    因子正交化器
    """
    def __init__(self, method='incremental', threshold=0.7):
        """
        参数:
            method: 'lowdin' or 'incremental'
            threshold: 相关性阈值 (增量方法用)
        """
        self.method = method
        self.threshold = threshold
        
    def lowdin_orthogonalize(self, factor_matrix):
        """
        Löwdin 对称正交化
        
        参数:
            factor_matrix: pd.DataFrame or np.ndarray (n_samples x n_factors)
            
        返回:
            正交化后的因子矩阵
        """
        if isinstance(factor_matrix, pd.DataFrame):
            factor_values = factor_matrix.values
            columns = factor_matrix.columns
            index = factor_matrix.index
        else:
            factor_values = factor_matrix
            columns = None
            index = None
        
        # 去除全为NaN的列
        valid_cols = ~np.all(np.isnan(factor_values), axis=0)
        factor_values = factor_values[:, valid_cols]
        
        if factor_values.shape[1] == 0:
            logger.warning("所有因子均为NaN,无法正交化")
            return pd.DataFrame() if columns is not None else np.array([])
        
        # 填充NaN为0 (简化处理)
        factor_values = np.nan_to_num(factor_values)
        
        # 1. 计算重叠矩阵 S = F^T * F
        S = factor_values.T @ factor_values
        
        # 2. 对称正交化: S^(-1/2)
        try:
            eigvals, eigvecs = np.linalg.eigh(S)
            
            # 处理小特征值 (避免数值不稳定)
            eigvals_safe = np.maximum(eigvals, 1e-10)
            
            # S^(-1/2) = V * diag(lambda^(-1/2)) * V^T
            S_inv_sqrt = eigvecs @ np.diag(1.0 / np.sqrt(eigvals_safe)) @ eigvecs.T
            
            # 3. 正交因子 = F * S^(-1/2)
            orthogonal_factors = factor_values @ S_inv_sqrt
            
            logger.info(f"Löwdin正交化完成: {factor_values.shape[1]} 个因子")
            
            if columns is not None:
                return pd.DataFrame(orthogonal_factors, columns=columns[valid_cols], index=index)
            else:
                return orthogonal_factors
                
        except np.linalg.LinAlgError as e:
            logger.error(f"正交化失败: {e}, 返回原始因子")
            if columns is not None:
                return pd.DataFrame(factor_values, columns=columns[valid_cols], index=index)
            else:
                return factor_values
    
    def incremental_deduplication(self, new_factor, existing_factors, dates=None, threshold=None):
        """
        增量去重：检查新因子是否与已有因子高度相关
        
        参数:
            new_factor: pd.Series or np.ndarray - 新因子
            existing_factors: pd.DataFrame - 已有因子池
            dates: pd.Series/np.array - 对应的交易日数组(A股必须每天分开算截面相关性)
            threshold: float - 相关性阈值 (默认使用初始化的threshold)
            
        返回:
            (is_unique: bool, max_corr: float, most_similar_factor: str/None)
        """
        if threshold is None:
            threshold = self.threshold
            
        if existing_factors is None or existing_factors.empty:
            return True, 0.0, None
        
        # 转换为Series
        if isinstance(new_factor, np.ndarray):
            new_factor = pd.Series(new_factor, index=existing_factors.index)
        
        # 如果没有给定 date，强行回退到扁平序列相关性（非常不推荐但为了兼容）
        if dates is None:
            logger.warning("No dates provided to orthogonalizer, falling back to 1D Pearson correlation (Not Recommended)")
            correlations = {}
            for col in existing_factors.columns:
                existing = existing_factors[col]
                common_idx = new_factor.index.intersection(existing.index)
                if len(common_idx) < 10:
                    continue
                corr = new_factor.loc[common_idx].corr(existing.loc[common_idx], method='spearman')
                if not np.isnan(corr):
                    correlations[col] = abs(corr)
        else:
            # A股实战标准：Daily Cross-sectional Spearman Rank Correlation 平均值
            df = pd.DataFrame({'new': new_factor, 'date': dates})
            for col in existing_factors.columns:
                df[col] = existing_factors[col]
                
            correlations = {}
            for col in existing_factors.columns:
                # 按照日期groupby计算每天的斯皮尔曼相关性
                def _daily_spearman(sub_df):
                    if len(sub_df) < 5: return np.nan
                    return sub_df['new'].corr(sub_df[col], method='spearman')
                    
                daily_corrs = df.groupby('date').apply(_daily_spearman)
                mean_corr = daily_corrs.mean()
                if not np.isnan(mean_corr):
                    correlations[col] = abs(mean_corr)
        
        if not correlations:
            return True, 0.0, None
        
        # 找到最大相关性
        most_similar = max(correlations, key=correlations.get)
        max_corr = correlations[most_similar]
        
        is_unique = max_corr < threshold
        
        if not is_unique:
            logger.info(f"因子被拒绝: 与 '{most_similar}' 相关性={max_corr:.3f} >= {threshold}")
        else:
            logger.info(f"因子接受: 最大相关性={max_corr:.3f} < {threshold}")
        
        return is_unique, max_corr, most_similar
    
    def schmidt_orthogonalize(self, factor_matrix):
        """
        Gram-Schmidt 正交化 (经典方法)
        
        将因子逐一正交化，每个新因子减去在已有因子上的投影
        """
        if isinstance(factor_matrix, pd.DataFrame):
            factor_values = factor_matrix.values
            columns = factor_matrix.columns
            index = factor_matrix.index
        else:
            factor_values = factor_matrix
            columns = None
            index = None
        
        factor_values = np.nan_to_num(factor_values)
        n_samples, n_factors = factor_values.shape
        
        orthogonal_factors = np.zeros_like(factor_values)
        
        for i in range(n_factors):
            # 当前因子
            v = factor_values[:, i].copy()
            
            # 减去在已有正交因子上的投影
            for j in range(i):
                u = orthogonal_factors[:, j]
                # Projection: (v · u) / (u · u) * u
                proj = np.dot(v, u) / (np.dot(u, u) + 1e-10) * u
                v = v - proj
            
            # 归一化
            norm = np.linalg.norm(v)
            if norm > 1e-10:
                orthogonal_factors[:, i] = v / norm
            else:
                # 如果因子变为零向量,说明完全线性相关,保持为零
                orthogonal_factors[:, i] = 0
                logger.warning(f"因子 #{i} 与前序因子线性相关, 已去除")
        
        logger.info(f"Schmidt正交化完成: {n_factors} 个因子")
        
        if columns is not None:
            return pd.DataFrame(orthogonal_factors, columns=columns, index=index)
        else:
            return orthogonal_factors


def batch_filter_factors(factors_dict,threshold=0.7, method='incremental'):
    """
    批量过滤因子，去除高相关因子
    
    参数:
        factors_dict: dict {factor_name: factor_values}
        threshold: 相关性阈值
        method: 'incremental' or 'lowdin'
        
    返回:
        filtered_dict: dict - 过滤后的因子字典
        rejection_log: list - 被拒绝的因子及原因
    """
    orthogonalizer = Orthogonalizer(method=method, threshold=threshold)
    
    filtered_dict = {}
    rejection_log = []
    
    # 逐个添加因子,检查正交性
    for name, factor_values in factors_dict.items():
        if not filtered_dict:
            # 第一个因子直接加入
            filtered_dict[name] = factor_values
            logger.info(f"添加因子: {name} (首个因子)")
        else:
            # 转换为DataFrame用于检查
            existing_df = pd.DataFrame(filtered_dict)
            
            is_unique, max_corr, most_similar = orthogonalizer.incremental_deduplication(
                factor_values, existing_df, threshold=threshold
            )
            
            if is_unique:
                filtered_dict[name] = factor_values
            else:
                rejection_log.append({
                    'factor': name,
                    'reason': f'与 {most_similar} 相关性={max_corr:.3f} >= {threshold}'
                })
    
    logger.info(f"过滤完成: 保留 {len(filtered_dict)}/{len(factors_dict)} 个因子")
    
    return filtered_dict, rejection_log


# 示例使用
if __name__ == "__main__":
    print("=" * 60)
    print("因子正交化示例")
    print("=" * 60)
    
    # 生成模拟因子：3个因子,其中2个高度相关
    np.random.seed(42)
    n = 1000
    
    factor1 = np.random.randn(n)
    factor2 = 0.9 * factor1 + 0.1 * np.random.randn(n)  # 与factor1高度相关
    factor3 = np.random.randn(n)  # 独立因子
    
    factors_dict = {
        'momentum': pd.Series(factor1),
        'momentum_v2': pd.Series(factor2),
        'volatility': pd.Series(factor3)
    }
    
    # 测试增量去重
    print("\n【增量去重测试】")
    filtered, rejected = batch_filter_factors(factors_dict, threshold=0.7)
    print(f"\n保留因子: {list(filtered.keys())}")
    print(f"拒绝因子: {rejected}")
    
    # 测试Löwdin正交化
    print("\n【Löwdin正交化测试】")
    factor_matrix = pd.DataFrame(factors_dict)
    orthogonalizer = Orthogonalizer()
    orthogonal_factors = orthogonalizer.lowdin_orthogonalize(factor_matrix)
    
    print(f"\n正交化前相关性矩阵:")
    print(factor_matrix.corr().round(3))
    
    print(f"\n正交化后相关性矩阵:")
    print(orthogonal_factors.corr().round(3))
    
    print("\n" + "=" * 60)
