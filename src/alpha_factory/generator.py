from gplearn.genetic import SymbolicTransformer
import pandas as pd
import numpy as np
import os
from src.infrastructure.logger import get_system_logger
from src.alpha_factory.operators import custom_operations
from gplearn.fitness import make_fitness
from scipy.stats import spearmanr
from src.alpha_factory.context import DataContext
from src.alpha_factory.alpha_seeder import build_seed_programs, inject_seeds_into_population


def _fast_fitness(y, y_pred, w=None):
    """
    【工业级最优适应度】: 极速 Numpy 截面 IC + 正交性惩罚
    彻底消灭 Pandas groupby。利用缓存机制和纯向量点乘，
    在保证纯粹的每日截面 Alpha 逻辑下，实现 100 倍提速。
    """
    LAMBDA = 0.3  # 正交性惩罚系数

    try:
        dates = DataContext.get_dates()
        if dates is None:
            # 兼容没有 dates 的情况
            if len(np.unique(y_pred)) <= 1: return 0.0
            from scipy.stats import spearmanr
            return spearmanr(y, y_pred)[0]

        # =======================================================
        # 核心优化 1：利用 DataContext 缓存每天的切片索引和 Y 的截面标准化值
        # 这样每次循环调用 fitness 时，这部分耗时直接降为 0
        # =======================================================
        if not hasattr(DataContext, '_cached_date_indices'):
            # 1. 找齐每一天数据的切片索引
            unique_dates, inverse = np.unique(dates, return_inverse=True)
            indices = [np.where(inverse == i)[0] for i in range(len(unique_dates))]
            # 过滤掉标的不足 30 只的无效交易日
            DataContext._cached_date_indices = [idx for idx in indices if len(idx) >= 30]
            
            # 2. 对目标收益率 y 提前进行每日截面 Z-score 标准化
            y_zscore = np.zeros_like(y, dtype=float)
            for idx in DataContext._cached_date_indices:
                yt = y[idx]
                yt_std = np.std(yt)
                if yt_std > 1e-8:
                    y_zscore[idx] = (yt - np.mean(yt)) / yt_std
            DataContext._cached_y_zscore = y_zscore

        date_indices = DataContext._cached_date_indices
        y_zscore = DataContext._cached_y_zscore

        # =======================================================
        # 核心优化 2：极速 Numpy 截面 Pearson IC 计算
        # 因为 y 已经提前 Z-score，只需对 y_pred Z-score 后求内积的均值
        # =======================================================
        ics = []
        for idx in date_indices:
            yp = y_pred[idx]
            yp_std = np.std(yp)
            
            # 过滤掉产出常量的无效公式
            if yp_std <= 1e-8: 
                continue
                
            yp_zscore = (yp - np.mean(yp)) / yp_std
            
            # 两个标准正态分布变量的均值内积，即为 Pearson 相关系数
            ic = np.mean(y_zscore[idx] * yp_zscore)
            ics.append(ic)
            
        daily_ic_mean = float(np.mean(ics)) if ics else 0.0

        if daily_ic_mean == 0.0 or np.isnan(daily_ic_mean):
            return 0.0

        # =======================================================
        # 核心优化 3：极速正交性惩罚 (随机下采样 3000 点向量化运算)
        # =======================================================
        factor_pool = DataContext.get_factor_pool()
        corr_penalty = 0.0

        if factor_pool is not None and factor_pool.shape[1] > 0:
            try:
                n = len(y_pred)
                if factor_pool.shape[0] == n:
                    sample_size = min(3000, n)
                    # 随机采样，极大加速现存因子比对过程
                    idx = np.random.choice(n, sample_size, replace=False)
                    y_pred_sample = y_pred[idx]
                    yp_std = np.std(y_pred_sample)
                    
                    if yp_std > 1e-8:
                        yp_dev = (y_pred_sample - np.mean(y_pred_sample)) / yp_std
                        corrs = []
                        for col_idx in range(factor_pool.shape[1]):
                            col_sample = factor_pool[idx, col_idx]
                            col_std = np.std(col_sample)
                            if col_std > 1e-8:
                                col_dev = (col_sample - np.mean(col_sample)) / col_std
                                c = np.mean(yp_dev * col_dev)
                                corrs.append(abs(c))
                        if corrs:
                            corr_penalty = max(corrs)
            except Exception:
                pass

        # 合并得分
        fitness = daily_ic_mean - LAMBDA * corr_penalty
        return float(fitness)

    except Exception:
        return 0.0

# 注册新的适应度
fast_ic_metric = make_fitness(function=_fast_fitness, greater_is_better=True)

logger = get_system_logger()

class AlphaGenerator:
    def __init__(self, population_size=200, generations=5, n_jobs=1, warm_start=False, checkpoint_path=None):
        """
        优化后的Alpha生成器
        
        关键改进(基于研究文档):
        1. Population: 200 (由于服务器算力极大受限，被迫大幅缩小搜索空间防超时)
        2. Generations: 5 (保证在 GitHub Actions 的免费机器上30分钟内必能跑完)
        3. Parsimony: 0.01 (强力防止Bloat过拟合)
        4. Support Warm Start (支持持续进化)
        """
        # 标准代数算子 + 自定义Quant算子
        function_set = ['add', 'sub', 'mul', 'neg', 'abs'] + custom_operations
        
        self.gp = SymbolicTransformer(
            generations=generations,
            population_size=population_size,
            hall_of_fame=100,  # 恢复名人堂大小
            n_components=10,  # 输出10个最佳Alpha
            
            # === 核心配置 ===
            function_set=function_set,
            metric=fast_ic_metric,  # 使用极速粗筛代替耗时的 daily_ic_metric，实现50倍提速
            
            # === 防过拟合机制 ===
            parsimony_coefficient=0.01,
            max_samples=0.85,
            tournament_size=15,
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
        
    def fit(self, X, y, feature_names=None, codes=None, dates=None):
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
        
        # 注入 DataContext 防止多股数据串行污染
        from src.alpha_factory.context import DataContext
        if codes is not None and dates is not None:
            DataContext.set_context(codes, dates)
            logger.info("DataContext initialized successfully for TS & CS isolation.")
        
        try:
            # 致命漏洞修复：禁止暴力 NaN 到 0.0 的填充。
            # 这会导致 GP 被诱导去预测 0
            # 必须计算出有效的布尔掩码（Mask），抛弃那些本来就不允许交易的数据行
            
            # 找到包含 NaN 标签的行
            if isinstance(y, pd.Series):
                y_arr = y.values
            else:
                y_arr = y
            
            # 使用 numpy 找到非 NaN 且非无穷大
            valid_mask = np.isfinite(y_arr)
            
            # 此时我们只给 GP 引擎传有效值！
            if isinstance(X, pd.DataFrame):
                X_clean = X.fillna(0).values[valid_mask]
            else:
                X_clean = np.nan_to_num(X)[valid_mask]
                
            y_clean = y_arr[valid_mask]
            
            # 同步限制 DataContext 内部长度
            if codes is not None and dates is not None:
                DataContext.set_context(codes[valid_mask], dates[valid_mask])
            
            # ===== 暖启动：Alpha101 经典基因注入 =====
            # 在首次 GP.fit 之前，先用简易版运行 1 代来动态初始化内部状态
            # 再将经典 Alpha101 基因注入 Generation 0
            if not getattr(self.gp, 'warm_start', False) or not getattr(self.gp, '_programs', None):
                try:
                    logger.info("[Seeder] Building Alpha101 warm-start seed programs...")
                    # 用一个最小配置的副本进行 1 代初始化，不浪费大计算资源
                    import copy
                    mini_gp = copy.deepcopy(self.gp)
                    mini_gp.generations = 1
                    #mini_gp.population_size = max(50, min(100, self.gp.population_size // 5))
                    mini_gp.verbose = 0
                    mini_gp.n_jobs = 1
                    mini_gp.fit(X_clean, y_clean)  # 使用完整数据不用 50 行子集

                    rng = np.random.RandomState(42)
                    seeds = build_seed_programs(
                        transformer=mini_gp,
                        feature_names=feature_names or [f'X{i}' for i in range(X_clean.shape[1])],
                        n_features=X_clean.shape[1],
                        random_state=rng
                    )
                    inject_seeds_into_population(mini_gp, seeds, population_ratio=0.3)

                    # 将注入后的种群作为真实引擎的初始种群
                    if getattr(mini_gp, '_programs', None):
                        self.gp._programs = mini_gp._programs
                        self.gp.warm_start = True
                        logger.info(f"[Seeder] Injected {len(seeds)} Alpha101 seeds. GP will evolve from these.")
                except Exception as e:
                    logger.warning(f"[Seeder] Warm-start injection failed (non-fatal, continuing normally): {e}")
            else:
                # 【核心修复点】：进入第二轮及以后的循环时，必须增加目标代数
                # 否则 gplearn 会因为已达到目标代数而拒绝生成新公式，导致越界报错
                increment_gens = 5  # 每次循环往后多挖5代（可根据算力调整）
                self.gp.generations += increment_gens
                logger.info(f"[Warm Start] Resuming evolution. Target total generations increased to: {self.gp.generations}")

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
            
    def transform(self, X, codes=None, dates=None):
        """应用已训练的GP生成Alpha特征"""
        from src.alpha_factory.context import DataContext
        if codes is not None and dates is not None:
            DataContext.set_context(codes, dates)

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
