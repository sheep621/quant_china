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
        # 调用你刚刚写好的排序数据预处理方法
        X, y, group = self._prepare_ranking_data(df, features, label_col=label)
        
        # 必须把 group 传进去，这是 Lambdarank 不报错的关键！
        dataset = lgb.Dataset(X, label=y, group=group)
        return dataset

    def train(self, df_train, features, label):
        logger.info("Training LGBM Model with LambdaRank...")
        
        # 核心改造 2：防过拟合的内部验证集切分
        dates = sorted(df_train['date'].unique())
        split_idx = int(len(dates) * 0.9)
        split_date = dates[split_idx]

        inner_train_df = df_train[df_train['date'] < split_date]
        inner_val_df = df_train[df_train['date'] >= split_date]

        if inner_train_df.empty or inner_val_df.empty:
            logger.warning("Not enough dates to split inner validation. Using full train.")
            inner_train_df = df_train
            inner_val_df = df_train

        # 使用更新后的 _prepare_lgb_data 构建带有 group 参数的训练集
        dtrain = self._prepare_lgb_data(inner_train_df, features, label)
        
        # 如果有验证集，验证集也必须带有 group 参数，并且指定 reference 为 train_set
        X_va, y_va, g_va = self._prepare_ranking_data(inner_val_df, features, label_col=label)
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

            # 使用更新后的 _prepare_lgb_data 构建带有 group 参数的训练集
            dtrain = self._prepare_lgb_data(inner_train_df, features, label)
            
            # 如果有验证集，验证集也必须带有 group 参数，并且指定 reference 为 train_set
            X_va, y_va, g_va = self._prepare_ranking_data(inner_val_df, features, label_col=label)
            dval = lgb.Dataset(X_va, label=y_va, group=g_va, reference=dtrain)

            model = lgb.train(
                self.default_params,
                dtrain,
                num_boost_round=1000,
                valid_sets=[dval],
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
            )

            # 在纯净的测试集上预测，并计算截面 Rank IC 代替 RMSE
            # 测试集无需变换为分箱数据，直接使用原始特征推理
            df_test_sorted = df_test_fold.sort_values('date').copy()
            preds = model.predict(df_test_sorted[features].values, num_iteration=model.best_iteration)
            df_test_sorted['pred'] = preds
            
            def _daily_ic(sub):
                if len(sub) > 1: return sub[label].corr(sub['pred'], method='spearman')
                return np.nan
                
            daily_ic = df_test_sorted.groupby('date', group_keys=False).apply(_daily_ic).mean()
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

    def _prepare_ranking_data(self, df, features, label_col='label', n_bins=5):
        """
        核心改造：将连续收益率转换为 Lambdarank 需要的离散整数标签，并生成 group 参数
        """
        # 1. 必须按日期排序，这是 Lambdarank 分组计算 NDCG 的绝对前提
        df_sorted = df.sort_values('date').copy()
        
        # 2. 截面分箱：每天按收益率将股票分为 n_bins 档 (例如 0, 1, 2, 3, 4)
        # qcut 会自动处理排名，duplicates='drop' 防止遇到大面积停牌/一字板时分箱报错
        df_sorted['label_int'] = df_sorted.groupby('date')[label_col].transform(
            lambda x: pd.qcut(x, q=n_bins, labels=False, duplicates='drop')
        )
        
        # 填充异常值（比如某天全市场停牌）为中间档位，并强制转为 int
        df_sorted['label_int'] = df_sorted['label_int'].fillna(n_bins // 2).astype(int)
        
        # 3. 计算每天的股票数量 (query_lengths)，这是 Lambdarank 必须的 group 参数
        group_sizes = df_sorted.groupby('date').size().values
        
        X = df_sorted[features]
        y = df_sorted['label_int']
        
        return X, y, group_sizes

    def save_model(self, path):
        if self.model: self.model.save_model(path)

    def load_model(self, path):
        self.model = lgb.Booster(model_file=path)