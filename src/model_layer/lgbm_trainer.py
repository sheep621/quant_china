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
        
        # 🔴 FIX: 只有在有验证集时才启用early_stopping
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
