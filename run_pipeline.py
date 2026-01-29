# import fire
import pandas as pd
import os
from datetime import datetime, timedelta
from src.infrastructure.logger import get_system_logger
from src.data_engine.loader import DataLoader
from src.data_engine.cleaner import DataCleaner
from src.alpha_factory.generator import AlphaGenerator
from src.model_layer.lgbm_trainer import LGBMTrainer
from src.execution.backtest import Backtester

logger = get_system_logger()

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
            df = pd.read_parquet(f)
            df = self.cleaner.process_daily_data(df)
            if df is not None:
                all_dfs.append(df)
                
        if not all_dfs:
            return None
            
        full_df = pd.concat(all_dfs, ignore_index=True)
        return full_df

    def train_model(self):
        df = self.build_dataset()
        if df is None: return
        
        # Feature Engineering: Use AlphaGenerator
        # We need to drop rows where label is NaN for training
        df_mining = df.dropna(subset=['label'])
        
        # Base features for mining
        base_features = ['turn', 'pctChg', 'volume', 'amount', 'open', 'close', 'high', 'low']
        X_mining = df_mining[base_features]
        y_mining = df_mining['label']
        
        # Initialize and Fit Generator
        # 🔴 FIX: 使用默认优化参数(1000/20),不要覆盖
        self.generator = AlphaGenerator(n_jobs=1)
        self.generator.fit(X_mining, y_mining)
        
        # Transform (Generate Alpha Factors)
        new_alphas = self.generator.transform(df[base_features])
        new_alpha_cols = [f"alpha_{i}" for i in range(new_alphas.shape[1])]
        
        df_alphas = pd.DataFrame(new_alphas, columns=new_alpha_cols, index=df.index)
        df = pd.concat([df, df_alphas], axis=1)
        
        # Features for Model are the new alphas
        features = new_alpha_cols
        logger.info(f"Generated {len(features)} alpha features via GP.")
        
        # Train / Val Split (Time based)
        dates = df['date'].unique()
        # Fix for pyarrow/pandas: unique() might return an ArrowExtensionArray which doesn't have sort
        if hasattr(dates, 'to_numpy'):
             dates = dates.to_numpy()
        dates.sort()
        split_idx = int(len(dates) * 0.8)
        split_date = dates[split_idx]
        
        df_train = df[df['date'] < split_date]
        df_val = df[df['date'] >= split_date]
        
        logger.info(f"Training on {len(df_train)} rows, Val on {len(df_val)} rows")
        
        # 1. Run Rolling CV for robust evaluation
        logger.info("Running Rolling Cross-Validation...")
        self.trainer.run_cv(df_train, features, label='label', n_splits=5)
        
        # 2. Final Train
        self.trainer.train(df_train, features, label='label', df_val=df_val)
        return self.trainer, features, df

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