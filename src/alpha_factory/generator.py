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
    【工业级最优适应度】: 极速 Numpy 截面 IC + 正交性惩罚 + 换手率惩罚(TC)
    """
    LAMBDA_ORTHO = 0.3  # 正交性相似度惩罚系数
    LAMBDA_TC = 0.15    # 换手率加分系数 (自相关性越高，换手率越低，给予额外奖励)

    try:
        dates = DataContext.get_dates()
        codes = getattr(DataContext, '_codes', None)
        if codes is None and hasattr(DataContext, 'get_codes'):
            codes = DataContext.get_codes()
            
        if dates is None:
            if len(np.unique(y_pred)) <= 1: return 0.0
            from scipy.stats import spearmanr
            return spearmanr(y, y_pred)[0]

        # --- 核心 1：极速截面 IC 计算 ---
        if not hasattr(DataContext, '_cached_date_indices'):
            unique_dates, inverse = np.unique(dates, return_inverse=True)
            valid_mask = getattr(DataContext, '_valid_mask', None)
            indices = []
            for i in range(len(unique_dates)):
                idx = np.where(inverse == i)[0]
                if valid_mask is not None:
                    idx = idx[valid_mask[idx]] # 剔除不可交易的涨跌停废点
                if len(idx) >= 30:
                    indices.append(idx)
            DataContext._cached_date_indices = indices
            
            y_zscore = np.zeros_like(y, dtype=float)
            for idx in DataContext._cached_date_indices:
                yt = y[idx]
                yt_std = np.std(yt)
                if yt_std > 1e-8:
                    y_zscore[idx] = (yt - np.mean(yt)) / yt_std
            DataContext._cached_y_zscore = y_zscore

        date_indices = DataContext._cached_date_indices
        y_zscore = DataContext._cached_y_zscore

        ics = []
        for idx in date_indices:
            yp = y_pred[idx]
            yp_std = np.std(yp)
            if yp_std <= 1e-8: continue
            yp_zscore = (yp - np.mean(yp)) / yp_std
            ic = np.mean(y_zscore[idx] * yp_zscore)
            ics.append(ic)
            
        daily_ic_mean = float(np.mean(ics)) if ics else 0.0
        if daily_ic_mean == 0.0 or np.isnan(daily_ic_mean): return 0.0

        # --- 核心 2：正交性惩罚 (随机下采样提速) ---
        factor_pool = DataContext.get_factor_pool()
        corr_penalty = 0.0
        valid_mask = getattr(DataContext, '_valid_mask', None)
        valid_indices = np.where(valid_mask)[0] if valid_mask is not None else np.arange(len(y_pred))
        
        if factor_pool is not None and factor_pool.shape[1] > 0 and len(valid_indices) > 0:
            try:
                if factor_pool.shape[0] == len(y_pred):
                    sample_size = min(3000, len(valid_indices))
                    idx = np.random.choice(valid_indices, sample_size, replace=False)
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
                        if corrs: corr_penalty = max(corrs)
            except Exception:
                pass

        # --- 核心 3：换手率惩罚 (TC) / 自相关性奖励 ---
        auto_corr = 0.0
        if codes is not None:
            try:
                # 获取该因子昨天的数据
                y_pred_lag = np.roll(y_pred, 1)
                # 生成掩码：保证边界计算时，必须是同一只股票 (今天code == 昨天code)
                same_code_mask = (codes == np.roll(codes, 1))
                if valid_mask is not None:
                    same_code_mask = same_code_mask & valid_mask
                    
                valid_idx = np.where(same_code_mask)[0]
                if len(valid_idx) > 0:
                    sample_size = min(5000, len(valid_idx))
                    idx = np.random.choice(valid_idx, sample_size, replace=False)
                    
                    yp_v = y_pred[idx]
                    ypl_v = y_pred_lag[idx]
                    yp_std, ypl_std = np.std(yp_v), np.std(ypl_v)
                    
                    if yp_std > 1e-8 and ypl_std > 1e-8:
                        yp_dev = (yp_v - np.mean(yp_v)) / yp_std
                        ypl_dev = (ypl_v - np.mean(ypl_v)) / ypl_std
                        auto_corr = np.mean(yp_dev * ypl_dev)  # 计算一阶自相关系数
            except Exception:
                pass

        # 最终得分：基础IC - 相似度惩罚 + 换手率奖励 (引导引擎寻找低频因子)
        return float(daily_ic_mean - LAMBDA_ORTHO * corr_penalty + LAMBDA_TC * auto_corr)
    except Exception:
        return 0.0



fast_ic_metric = make_fitness(function=_fast_fitness, greater_is_better=True)
logger = get_system_logger()

class AlphaGenerator:
    def __init__(self, population_size=200, generations=5, n_jobs=1, warm_start=False, checkpoint_path=None):
        function_set = ['add', 'sub', 'mul', 'neg', 'abs'] + custom_operations
        self.gp = SymbolicTransformer(
            generations=generations,
            population_size=population_size,
            hall_of_fame=100,
            n_components=10,
            function_set=function_set,
            metric=fast_ic_metric,
            parsimony_coefficient=0.01,
            max_samples=0.85,
            tournament_size=15,
            warm_start=warm_start,
            p_crossover=0.7,
            p_subtree_mutation=0.1,
            p_hoist_mutation=0.05,
            p_point_mutation=0.1,
            verbose=1,
            random_state=42,
            n_jobs=n_jobs
        )
        self.feature_names = None
        self.checkpoint_path = checkpoint_path
        if self.gp.warm_start and self.checkpoint_path:
            self._load_checkpoint()
        
    def fit(self, X, y, feature_names=None, codes=None, dates=None):
        self.feature_names = feature_names or (X.columns.tolist() if isinstance(X, pd.DataFrame) else None)
        
        logger.info(f"=== Alpha Mining Started ===")
        logger.info(f"Features: {X.shape[1]}, Samples: {X.shape[0]}")
        
        try:
            y_arr = y.values if isinstance(y, pd.Series) else y
            valid_mask = np.isfinite(y_arr)
            
            # 【关键修复】：传入完整数据保持连续性，缺测标签补 0 骗过 gplearn 检查！
            X_clean = X.fillna(0).values if isinstance(X, pd.DataFrame) else np.nan_to_num(X)
            y_clean = np.nan_to_num(y_arr, nan=0.0) 
            
            if codes is not None and dates is not None:
                DataContext.set_context(codes, dates)
                # 记录有效掩码，在 fitness 评估中执行“隐身”
                DataContext._valid_mask = valid_mask 

            if not getattr(self.gp, 'warm_start', False) or not getattr(self.gp, '_programs', None):
                try:
                    logger.info("[Seeder] Building Alpha101 warm-start seed programs...")
                    import copy
                    mini_gp = copy.deepcopy(self.gp)
                    mini_gp.generations = 1
                    mini_gp.verbose = 0
                    mini_gp.n_jobs = 1
                    mini_gp.fit(X_clean, y_clean) 

                    rng = np.random.RandomState(42)
                    seeds = build_seed_programs(
                        transformer=mini_gp,
                        feature_names=self.feature_names or [f'X{i}' for i in range(X_clean.shape[1])],
                        n_features=X_clean.shape[1],
                        random_state=rng
                    )
                    inject_seeds_into_population(mini_gp, seeds, population_ratio=0.3)

                    if getattr(mini_gp, '_programs', None):
                        self.gp._programs = mini_gp._programs
                        self.gp.warm_start = True
                        logger.info(f"[Seeder] Injected {len(seeds)} Alpha101 seeds.")
                except Exception as e:
                    logger.warning(f"[Seeder] Warm-start injection failed: {e}")
            else:
                self.gp.generations += 5
                logger.info(f"[Warm Start] Target total generations increased to: {self.gp.generations}")

            self.gp.fit(X_clean, y_clean)
            
            logger.info("=== GP Mining Completed ===")
            saved_alphas = []
            for i, prog in enumerate(self.gp._best_programs[:10]):
                if prog is None: continue
                fitness = prog.fitness_ if hasattr(prog, 'fitness_') else 0.0
                logger.info(f"  Alpha#{i+1} | Fitness={fitness:.4f} | {prog}")
                saved_alphas.append({'formula': str(prog), 'fitness': fitness})
                
            return saved_alphas
                
        except Exception as e:
            logger.error(f"GP Mining Failed: {e}")
            raise e
            
    def transform(self, X, codes=None, dates=None):
        if codes is not None and dates is not None:
            DataContext.set_context(codes, dates)
        X_clean = X.fillna(0).values if isinstance(X, pd.DataFrame) else np.nan_to_num(X)
        return self.gp.transform(X_clean)

    def _load_checkpoint(self):
        if not self.checkpoint_path or not os.path.exists(self.checkpoint_path): return
        import joblib
        try:
            saved_gp = joblib.load(self.checkpoint_path)
            if hasattr(saved_gp, '_programs'):
                self.gp._programs = saved_gp._programs
                self.gp._best_programs = getattr(saved_gp, '_best_programs', [])
                self.gp.run_details_ = getattr(saved_gp, 'run_details_', {})
                logger.info(f"Checkpoint loaded: {self.checkpoint_path}")
        except Exception as e: pass

    def save_checkpoint(self):
        if not self.checkpoint_path: return
        import joblib
        try:
            os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
            joblib.dump(self.gp, self.checkpoint_path)
        except Exception as e: pass