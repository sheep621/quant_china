from gplearn.genetic import SymbolicTransformer
import pandas as pd
import numpy as np
import os
from src.infrastructure.logger import get_system_logger
from src.alpha_factory.operators import custom_operations

logger = get_system_logger()

class AlphaGenerator:
    def __init__(self, population_size=1000, generations=20, n_jobs=1, warm_start=False, checkpoint_path=None):
        """
        优化后的Alpha生成器
        
        关键改进(基于研究文档):
        1. Population: 1000 (扩大搜索空间)
        2. Generations: 20 (充分进化)
        3. Parsimony: 0.01 (强力防止Bloat过拟合)
        4. Support Warm Start (支持持续进化)
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
            metric='spearman',  # RankIC核心
            
            # === 防过拟合机制 ===
            parsimony_coefficient=0.01,
            max_samples=0.8,
            tournament_size=30,
            warm_start=warm_start, # 支持热启动
            
            # === 多样性保护 ===
            p_crossover=0.7,
            p_subtree_mutation=0.1,
            p_hoist_mutation=0.05,
            p_point_mutation=0.1,
            
            # === 性能配置 ===
            verbose=1,
            random_state=42,
            n_jobs=n_jobs
        )
        self.feature_names = None
        self.checkpoint_path = checkpoint_path
        
        # 尝试加载增量断点
        if self.gp.warm_start and self.checkpoint_path:
            self._load_checkpoint()
        
    def fit(self, X, y, feature_names=None):
        """
        执行GP挖掘
        
        参数:
            X: 特征矩阵 (DataFrame优先,自动fillna)
            y: 目标Label (Open_T+2 / Open_T+1 - 1)
            feature_names: 特征列名列表 (可选)
        """
        self.feature_names = feature_names
        if feature_names is None and isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()

        logger.info(f"=== Alpha Mining Started ===")
        logger.info(f"Features: {X.shape[1]}, Samples: {X.shape[0]}")
        logger.info(f"GP Config: Pop={self.gp.population_size}, Gen={self.gp.generations}, WarmStart={self.gp.warm_start}")
        
        try:
            # NaN处理
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
            # Note: _best_programs is a list of programs
            # If warm_start is True, _best_programs accumulates? No, warm_start mainly affects population init.
            
            saved_alphas = []
            for i, prog in enumerate(self.gp._best_programs[:10]):
                if prog is None: continue
                # 如果有feature_names, 尝试格式化打印? 
                # gplearn 自动使用 X0, X1... 这里打印 raw formula 即可
                fitness = prog.fitness_ if hasattr(prog, 'fitness_') else 0.0
                logger.info(f"  Alpha#{i+1} | Fitness={fitness:.4f} | {prog}")
                saved_alphas.append({'formula': str(prog), 'fitness': fitness})
                
            return saved_alphas
                
        except Exception as e:
            logger.error(f"GP Mining Failed: {e}")
            raise e
            
    def transform(self, X):
        """应用已训练的GP生成Alpha特征"""
        if isinstance(X, pd.DataFrame):
            X_clean = X.fillna(0).values
        else:
            X_clean = np.nan_to_num(X)
            
        return self.gp.transform(X_clean)

    def _load_checkpoint(self):
        """加载历史种群，实现断点续训"""
        if not self.checkpoint_path or not os.path.exists(self.checkpoint_path):
            return
            
        import joblib
        try:
            saved_gp = joblib.load(self.checkpoint_path)
            # 恢复内部关键状态
            if hasattr(saved_gp, '_programs'):
                self.gp._programs = saved_gp._programs
                self.gp._best_programs = getattr(saved_gp, '_best_programs', [])
                self.gp.run_details_ = getattr(saved_gp, 'run_details_', {})
                logger.info(f"Checkpoint loaded from {self.checkpoint_path} with {len(self.gp._programs)} generations.")
        except Exception as e:
            logger.warning(f"Failed to load checkpoint from {self.checkpoint_path}: {e}")

    def save_checkpoint(self):
        """保存当前种群状态供下次启动"""
        if not self.checkpoint_path:
            return
            
        import joblib
        import os
        try:
            os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
            joblib.dump(self.gp, self.checkpoint_path)
            logger.info(f"Checkpoint saved to {self.checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
