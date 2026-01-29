from gplearn.genetic import SymbolicTransformer
import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger
from src.alpha_factory.operators import custom_operations

logger = get_system_logger()

class AlphaGenerator:
    def __init__(self, population_size=1000, generations=20, n_jobs=1):
        """
        优化后的Alpha生成器
        
        关键改进(基于研究文档):
        1. Population: 500 → 1000 (扩大搜索空间)
        2. Generations: 5 → 20 (充分进化)
        3. Parsimony: 0.001 → 0.01 (强力防止Bloat过拟合)
        4. Tournament_size: 20 → 30 (增加选择压力)
        5. Max_samples: 0.9 → 0.8 (降低过拟合)
        """
        # 标准代数算子 + 自定义Quant算子
        function_set = ['add', 'sub', 'mul', 'neg', 'abs'] + custom_operations
        
        self.gp = SymbolicTransformer(
            generations=generations,
            population_size=population_size,
            hall_of_fame=100,  # TOP 100保留
            n_components=20,    # 输出20个最佳Alpha
            
            # === 核心配置 ===
            function_set=function_set,
            metric='spearman',  # RankIC核心!直接优化Rank相关性
            
            # === 防过拟合机制 ===
            parsimony_coefficient=0.01,  # 复杂度惩罚!防止嵌套10层Rank
            max_samples=0.8,             # 每代仅用80%样本
            tournament_size=30,          # 竞标赛规模(选择压力)
            
            # === 多样性保护 ===
            p_crossover=0.7,     # 交叉概率
            p_subtree_mutation=0.1,
            p_hoist_mutation=0.05,
            p_point_mutation=0.1,
            
            # === 性能配置 ===
            verbose=1,
            random_state=42,
            n_jobs=n_jobs,
            
            # === 结构限制 ===
            init_depth=(2, 6),   # 初始深度范围
            max_depth=8          # 最大深度限制(防Bloat)
        )
        
    def fit(self, X, y):
        """
        执行GP挖掘
        
        参数:
            X: 特征矩阵 (DataFrame优先,自动fillna)
            y: 目标Label (下期收益)
        """
        logger.info(f"=== Alpha Mining Started ===")
        logger.info(f"Features: {X.shape[1]}, Samples: {X.shape[0]}")
        logger.info(f"GP Config: Pop={self.gp.population_size}, Gen={self.gp.generations}")
        logger.info(f"Parsimony={self.gp.parsimony_coefficient} (防Bloat)")
        
        try:
            # NaN处理:gplearn不接受NaN
            if isinstance(X, pd.DataFrame):
                X_clean = X.fillna(0).values
            else:
                X_clean = np.nan_to_num(X)
                
            y_clean = np.nan_to_num(y)
            
            # 执行进化
            self.gp.fit(X_clean, y_clean)
            
            logger.info("=== GP Mining Completed ===")
            
            # 输出TOP Alphas
            logger.info("TOP 5 Discovered Alphas:")
            for i, prog in enumerate(self.gp._best_programs[:5]):
                fitness = prog.fitness_
                logger.info(f"  Alpha#{i+1} | Fitness={fitness:.4f} | {prog}")
                
        except Exception as e:
            logger.error(f"GP Mining Failed: {e}")
            raise e
            
    def transform(self, X):
        """
        应用已训练的GP生成Alpha特征
        """
        if isinstance(X, pd.DataFrame):
            X_clean = X.fillna(0).values
        else:
            X_clean = np.nan_to_num(X)
            
        return self.gp.transform(X_clean)
