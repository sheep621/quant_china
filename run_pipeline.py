# import fire
import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime, timedelta
from src.infrastructure.logger import get_system_logger
from src.data_engine.loader import DataLoader
from src.data_engine.cleaner import DataCleaner
from src.alpha_factory.generator import AlphaGenerator
from src.model_layer.lgbm_trainer import LGBMTrainer
from src.execution.backtest import Backtester

logger = get_system_logger()

# 屏蔽 GP 随机生成垃圾公式时必然产生的数学警告
warnings.filterwarnings('ignore', category=RuntimeWarning)
np.seterr(all='ignore')

class QuantPipeline:
    def __init__(self):
        self.loader = DataLoader()
        self.cleaner = DataCleaner()
        self.trainer = LGBMTrainer()
        self.backtester = Backtester()
        
    def download_data(self, start_date="2020-01-01", end_date="2023-12-31"):
        """Download data for built-in list (simple version)"""
        logger.info("Initializing Login...")
        if not self.loader.login():
            return
            
        # Scheme A: Download ALL stocks (Full Market)
        all_codes = self.loader.get_stock_list()
        
        # Incremental check: Filter out codes that already have up-to-date data?
        # For simplicity, we just target all. The Loader has a basic check.
        target_codes = all_codes
        
        logger.info(f"Targeting FULL MARKET: {len(target_codes)} stocks. This may take a while...")
        
        self.loader.update_data(target_codes, start_date, end_date)
        self.loader.logout()
        return target_codes

    def build_dataset(self):
        """Load all raw data and process into a single DF for training"""
        data_dir = "data/raw"
        all_dfs = []
        import glob
        files = glob.glob(f"{data_dir}/*.parquet")
        
        if not files:
            logger.warning("No data found. Run download_data first.")
            return None
            
        logger.info(f"Loading {len(files)} files...")
        for f in files:
            try:
                df = pd.read_parquet(f)
                all_dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to load {f}: {e}")
                
        if not all_dfs:
            return None
            
        full_df = pd.concat(all_dfs, ignore_index=True)
        
        # --- FIX: Time Filter to drastically reduce GP/Training workload on CI ---
        # Instead of crunching 10+ years of full market data, we slice the last 2 years.
        if 'date' in full_df.columns:
            full_df['date'] = pd.to_datetime(full_df['date'])
            max_date = full_df['date'].max()
            cutoff_date = max_date - pd.DateOffset(years=2)
            full_df = full_df[full_df['date'] >= cutoff_date]
            logger.info(f"Sliced data to > {cutoff_date.date()} for faster CI Execution. Total rows: {len(full_df)}")
        
        # Apply cleaner on the combined dataframe to enable cross-sectional operations (e.g. Rank, MAD)
        full_df = self.cleaner.process_daily_data(full_df)
        return full_df

    def train_model(self):
        df = self.build_dataset()
        if df is None: return
        
        # --- FIX: Time-based Split MUST be done BEFORE Alpha Mining ---
        logger.info("Splitting Train/Val dataset to prevent Look-Ahead Bias...")
        dates = df['date'].unique()
        if hasattr(dates, 'to_numpy'):
             dates = dates.to_numpy()
        dates.sort()
        split_idx = int(len(dates) * 0.8)
        split_date = dates[split_idx]
        
        df_train_raw = df[df['date'] < split_date].copy()
        df_val_raw   = df[df['date'] >= split_date].copy()
        logger.info(f"Training on {len(df_train_raw)} rows, Val on {len(df_val_raw)} rows")
        
        # Feature Engineering: Use AlphaGenerator only on TRAIN set
        df_mining = df_train_raw.copy()
        
        # Extract features dynamically to avoid discarding new cleaned features
        exclude_cols = ['date', 'code', 'label', 'next_open', 'next_2_open', 'is_limit_up', 'is_limit_down', 'next_is_limit_up', 'next_is_limit_down', 'next_2_is_limit_down', 'tradestatus', 'high_limit', 'limit_ratio', 'isST', 'adjustflag', 'is_tradable']
        base_features = [c for c in df_mining.columns if c not in exclude_cols]
        X_mining = df_mining[base_features]
        y_mining = df_mining['label']
        
        # Initialize and Fit Generator
        # 🔴 FIX: 必须传入 codes 和 dates 以激活 DataContext 防止跨股票/跨时空的未来数据穿越
        codes_mining = df_mining['code'].values
        dates_mining = df_mining['date'].values
        
        self.generator = AlphaGenerator(n_jobs=1)
        self.generator.fit(
            X_mining, y_mining,
            feature_names=base_features,
            codes=codes_mining,
            dates=dates_mining
        )
        
        # Transform (Generate Alpha Factors for full dataset)
        new_alphas = self.generator.transform(
            df[base_features],
            codes=df['code'].values,
            dates=df['date'].values
        )
        new_alpha_cols = [f"alpha_{i}" for i in range(new_alphas.shape[1])]
        
        df_alphas = pd.DataFrame(new_alphas, columns=new_alpha_cols, index=df.index)
        df_enriched = pd.concat([df, df_alphas], axis=1)
        
        # Features for Model are the new alphas
        features = new_alpha_cols
        logger.info(f"Generated {len(features)} alpha features via GP.")
        
        # ============== 新增：任务 4.1 特征截面标准化 (极速向量化版) ==============
        logger.info("Applying Cross-Sectional Z-Score standardization to all ML features...")
        features_to_normalize = base_features + new_alpha_cols
        
        # 避免缓慢的 for 循环 lambda，直接使用 Pandas 的向量化底层 C 引擎计算
        grouped = df_enriched.groupby('date')[features_to_normalize]
        mean_df = grouped.transform('mean')
        std_df = grouped.transform('std')
        
        # 极速全局去均值除以标准差
        df_enriched[features_to_normalize] = (df_enriched[features_to_normalize] - mean_df) / (std_df + 1e-8)
        # ==========================================================

       
        df_train = df_enriched[df_enriched['date'] < split_date]
        df_val   = df_enriched[df_enriched['date'] >= split_date]
        
        # 1. Run Rolling CV for robust evaluation
        logger.info("Running Rolling Cross-Validation on strictly historical train set...")
        self.trainer.run_cv(df_train, features, label='label', n_splits=5)
        
        # 2. Final Train (不再传入外部的 df_val，完全交由模型内部切分以防泄露)
        self.trainer.train(df_train, features, label='label')
        
        # 为了让后续的回测模块有完整的数据可用，返回 df_enriched
        return self.trainer, features, df_enriched

    def run_backtest(self):
        # 1. Train and get enriched DF
        # 🔴 FIX: 安全解包,防止train_model返回None时崩溃
        result = self.train_model()
        if result is None: 
            logger.error("Training failed, cannot run backtest")
            return
        trainer, features, df = result
        
        # 2. Backtest loop using the SAME dataframe (with alphas)
        # Note: In production, we would save the generator and transform fresh data.
        # Here we just reuse the in-memory DF for simulation.
        
        # Sort by date
        dates = sorted(df['date'].unique())
        # Use validation period for backtest
        start_idx = int(len(dates) * 0.8)
        test_dates = dates[start_idx:]
        
        logger.info(f"Starting Backtest on {len(test_dates)} trading days...")
        
        for date in test_dates:
            daily_slice = df[df['date'] == date]
            
            # 1. Predict
            if daily_slice.empty: continue
            
            # Prepare dict for execution
            # {code: {open, close...}}
            daily_data_dict = daily_slice.set_index('code').to_dict('index')
            
            # Predict
            preds = trainer.predict(daily_slice, features)
            alpha_scores = dict(zip(daily_slice['code'], preds))
            
            # Execute
            self.backtester.execute_daily(date, alpha_scores, daily_data_dict)
            
        # Result
        metrics = self.backtester.get_metrics()
        logger.info(f"Backtest Result: {metrics}")

if __name__ == '__main__':
    import sys
    pipeline = QuantPipeline()
    if len(sys.argv) > 1 and sys.argv[1] == 'download_data':
        pipeline.download_data()
    else:
        pipeline.run_backtest()