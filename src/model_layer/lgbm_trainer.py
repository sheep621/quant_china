import lightgbm as lgb
import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class LGBMTrainer:
    def __init__(self, params=None):
        # 核心改造 1：从回归 (Regression) 升级为排序 (Ranking)
        self.default_params = {
            'objective': 'lambdarank', # 优化 NDCG 排序指标
            'metric': 'ndcg',          
            'eval_at': [5, 10, 20],    # 重点关注头部 Top 5/10/20 的命中率
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': 5,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'n_jobs': -1,
            'verbose': -1,
            'random_state': 42
        }
        if params:
            self.default_params.update(params)
        self.model = None

    def _prepare_lgb_data(self, df, features, label):
        """
        内部辅助函数：LambdaRank 强制要求同组(同一天)的数据必须挨在一起，
        且需要提供 group 数组告诉模型每天有多少行。
        """
        # 必须按日期排序，确保截面数据连续
        df_sorted = df.sort_values('date').copy()
        X = df_sorted[features].values
        y = df_sorted[label].values
        # 统计每一天的样本数，作为 group 参数
        group = df_sorted.groupby('date', sort=False).size().values
        return X, y, group, df_sorted

    def train(self, df_train, features, label):
        logger.info("Training LGBM Model with LambdaRank...")
        
        # 核心改造 2：防过拟合的内部验证集切分
        # 从训练集中切出最后 10% 的时间作为 early stopping 的真实依据
        dates = sorted(df_train['date'].unique())
        split_idx = int(len(dates) * 0.9)
        split_date = dates[split_idx]

        inner_train_df = df_train[df_train['date'] < split_date]
        inner_val_df = df_train[df_train['date'] >= split_date]

        if inner_train_df.empty or inner_val_df.empty:
            logger.warning("Not enough dates to split inner validation. Using full train.")
            inner_train_df = df_train
            inner_val_df = df_train

        X_tr, y_tr, g_tr, _ = self._prepare_lgb_data(inner_train_df, features, label)
        X_va, y_va, g_va, _ = self._prepare_lgb_data(inner_val_df, features, label)

        dtrain = lgb.Dataset(X_tr, label=y_tr, group=g_tr)
        dval = lgb.Dataset(X_va, label=y_va, group=g_va, reference=dtrain)

        self.model = lgb.train(
            self.default_params,
            dtrain,
            num_boost_round=1000,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)]
        )
        logger.info(f"Training completed. Best iteration: {self.model.best_iteration}")

    def run_cv(self, df, features, label, n_splits=5):
        """
        核心改造 3：彻底隔离的 Rolling CV。
        测试集 (Test Fold) 沦为纯净盲盒，绝不参与 early_stopping。
        """
        logger.info(f"Running {n_splits}-fold Rolling CV with LambdaRank...")
        dates = sorted(df['date'].unique())
        fold_size = len(dates) // (n_splits + 1)
        
        cv_metrics = []

        for i in range(n_splits):
            train_start = dates[0]
            train_end = dates[(i + 1) * fold_size]
            test_end = dates[(i + 2) * fold_size if i < n_splits - 1 else -1]

            train_mask = (df['date'] >= train_start) & (df['date'] <= train_end)
            
            # T+2 Embargo (隔离带)：测试集起点延后两天，防止标签泄露给训练集末尾
            test_start_idx = dates.index(train_end) + 2
            if test_start_idx >= len(dates): break
            test_start = dates[test_start_idx]
            
            test_mask = (df['date'] >= test_start) & (df['date'] <= test_end)

            df_train_fold = df[train_mask].dropna(subset=[label])
            df_test_fold = df[test_mask].dropna(subset=[label]) 

            if df_train_fold.empty or df_test_fold.empty: continue

            # 再次为 CV 的当前折切分内部 Validation Set
            fold_dates = sorted(df_train_fold['date'].unique())
            inner_split_date = fold_dates[int(len(fold_dates) * 0.9)]
            
            inner_train_df = df_train_fold[df_train_fold['date'] < inner_split_date]
            inner_val_df = df_train_fold[df_train_fold['date'] >= inner_split_date]

            X_tr, y_tr, g_tr, _ = self._prepare_lgb_data(inner_train_df, features, label)
            X_va, y_va, g_va, _ = self._prepare_lgb_data(inner_val_df, features, label)
            X_te, y_te, g_te, df_test_sorted = self._prepare_lgb_data(df_test_fold, features, label)

            dtrain = lgb.Dataset(X_tr, label=y_tr, group=g_tr)
            dval = lgb.Dataset(X_va, label=y_va, group=g_va, reference=dtrain)

            model = lgb.train(
                self.default_params,
                dtrain,
                num_boost_round=1000,
                valid_sets=[dval],
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
            )

            # 在纯净的测试集上预测，并计算截面 Rank IC 代替 RMSE
            preds = model.predict(X_te, num_iteration=model.best_iteration)
            df_test_sorted['pred'] = preds
            
            def _daily_ic(sub):
                if len(sub) > 1: return sub[label].corr(sub['pred'], method='spearman')
                return np.nan
                
            daily_ic = df_test_sorted.groupby('date').apply(_daily_ic).mean()
            cv_metrics.append(daily_ic)
            
            logger.info(f"Fold {i+1}: Train -> {train_end.strftime('%Y-%m-%d')} | Test -> {test_end.strftime('%Y-%m-%d')} | OOS Rank IC: {daily_ic:.4f}")

        mean_ic = np.nanmean(cv_metrics) if cv_metrics else 0.0
        logger.info(f"Rolling CV Completed. Mean Out-of-Sample Rank IC: {mean_ic:.4f}")
        return mean_ic

    def predict(self, df, features):
        if self.model is None:
            raise ValueError("Model not trained yet!")
        # 推理阶段不需要 group
        return self.model.predict(df[features].values, num_iteration=self.model.best_iteration)

    def save_model(self, path):
        if self.model: self.model.save_model(path)

    def load_model(self, path):
        self.model = lgb.Booster(model_file=path)