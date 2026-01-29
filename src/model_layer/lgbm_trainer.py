import lightgbm as lgb
import pandas as pd
import numpy as np
import datetime
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class LGBMTrainer:
    def __init__(self, params=None):
        self.default_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'n_jobs': 4
        }
        if params:
            self.default_params.update(params)
        self.model = None

    def train(self, df_train, features, label='label', df_val=None):
        """
        Train the model
        df_train: DataFrame containing features and label
        """
        if df_train is None or df_train.empty:
            logger.error("Training data is empty")
            return None
        
        # Prepare datasets
        X_train = df_train[features]
        y_train = df_train[label]
        
        train_ds = lgb.Dataset(X_train, label=y_train)
        valid_sets = [train_ds]
        
        if df_val is not None:
            X_val = df_val[features]
            y_val = df_val[label]
            val_ds = lgb.Dataset(X_val, label=y_val, reference=train_ds)
            valid_sets.append(val_ds)
            
        logger.info(f"Starting training with {len(features)} features...")
        
        # 只有在有验证集时才启用early_stopping
        callbacks = [lgb.log_evaluation(period=50)]
        if df_val is not None and len(valid_sets) > 1:
            callbacks.append(lgb.early_stopping(stopping_rounds=50))
        
        self.model = lgb.train(
            self.default_params,
            train_ds,
            num_boost_round=1000,
            valid_sets=valid_sets,
            callbacks=callbacks
        )
        
        logger.info(f"Training finished. Best iteration: {self.model.best_iteration}")
        return self.model

    def run_cv(self, df, features, label='label', n_splits=5):
        """
        Run Rolling Time Series Cross-Validation
        Provides robust evaluation across different market regimes.
        """
        if df is None or df.empty: return {}
        
        dates = sorted(df['date'].unique())
        n_dates = len(dates)
        fold_size = n_dates // (n_splits + 1)
        
        scores = []
        logger.info(f"Starting Rolling CV with {n_splits} splits...")
        
        for i in range(n_splits):
            # Rolling Window:
            # Train: [0 : fold_size * (i+1)]
            # Test:  [fold_size * (i+1) : fold_size * (i+2)]
            train_end_idx = fold_size * (i + 1)
            test_end_idx = fold_size * (i + 2)
            
            if test_end_idx > n_dates: break
            
            split_date = dates[train_end_idx]
            test_end_date = dates[min(test_end_idx, n_dates-1)]
            
            train_mask = df['date'] < split_date
            val_mask = (df['date'] >= split_date) & (df['date'] < test_end_date)
            
            df_train_fold = df[train_mask]
            df_val_fold = df[val_mask]
            
            if df_train_fold.empty or df_val_fold.empty: continue
            
            # Train temp model for this fold
            # Use silent mode for CV
            params = self.default_params.copy()
            params['verbose'] = -1
            
            X_t = df_train_fold[features]
            y_t = df_train_fold[label]
            X_v = df_val_fold[features]
            y_v = df_val_fold[label]
            
            dtrain = lgb.Dataset(X_t, label=y_t)
            dval = lgb.Dataset(X_v, label=y_v, reference=dtrain)
            
            model = lgb.train(
                params, dtrain, num_boost_round=500,
                valid_sets=[dval],
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
            )
            
            # Record metric (RMSE)
            score = model.best_score['valid_0']['rmse']
            scores.append(score)
            logger.info(f"Fold {i+1}: Train vs Val({split_date} -> {test_end_date}) | RMSE={score:.4f}")
            
        mean_score = np.mean(scores) if scores else 0.0
        logger.info(f"Rolling CV Average RMSE: {mean_score:.4f}")
        return {'cv_rmse_mean': mean_score, 'cv_scores': scores}

    def predict(self, df, features):
        """
        Predict on new data
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
            
        if df is None or df.empty:
            return np.array([])
            
        X = df[features]
        return self.model.predict(X, num_iteration=self.model.best_iteration)

    def get_feature_importance(self):
        if self.model is None:
            return {}
        return dict(zip(self.model.feature_name(), self.model.feature_importance()))
