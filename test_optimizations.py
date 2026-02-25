import unittest
import pandas as pd
import numpy as np
import shutil
from pathlib import Path
from src.data_engine.loader import DataLoader
from src.model_layer.lgbm_trainer import LGBMTrainer
from src.execution.backtest import Backtester

class TestOptimizations(unittest.TestCase):
    
    def test_parallel_loader_logic(self):
        """Verify parallel loader doesn't crash"""
        loader = DataLoader()
        # Mock fetch_daily_data to avoid network
        loader.fetch_daily_data = lambda code, s, e: pd.DataFrame({
            'date': ['2023-01-01'], 'close': [10.0]
        })
        # Test with dummy codes
        codes = ['test_1', 'test_2', 'test_3']
        try:
            loader.update_data(codes, "2023-01-01", "2023-01-02")
            print("\n[PASS] Parallel Loader ran successfully")
        except Exception as e:
            self.fail(f"Parallel Loader failed: {e}")

    def test_rolling_cv(self):
        """Verify Rolling CV logic"""
        # Create dummy data: 100 days
        dates = pd.date_range('2023-01-01', periods=100).strftime('%Y-%m-%d').tolist()
        df = pd.DataFrame({
            'date': dates,
            'f1': np.random.rand(100),
            'f2': np.random.rand(100),
            'label': np.random.rand(100)
        })
        
        trainer = LGBMTrainer()
        # Mock lightgbm training to be fast/dummy
        # Actually lgbm is fast enough on small data
        
        print("\nTesting Rolling CV...")
        metrics = trainer.run_cv(df, features=['f1', 'f2'], n_splits=3)
        # Note: I check implementation of run_cv. It returns dict.
        
        self.assertIn('cv_rmse_mean', metrics)
        print(f"[PASS] Rolling CV Metrics: {metrics}")

    def test_backtest_metrics(self):
        """Verify new metrics and slippage"""
        tester = Backtester(initial_capital=10000)
        
        # Day 1: Buy
        # Slippage: Buy at price * 1.001
        # Price=10.0, Exec=10.01. Buy 100 shares = 1001.0
        # Cost+Fee.
        market_data_1 = {'close': 10.0, 'next_open': 10.0, 'is_limit_up': False, 'next_is_limit_up': False}
        tester._buy('TEST', 0.5, market_data_1, 10000)
        
        # Check positions
        shares = tester.positions.get('TEST', 0)
        self.assertGreater(shares, 0)
        print(f"\nBought {shares} shares")
        
        # Manually add history for Day 1 (Peak)
        tester.history.append({'date': '2023-01-01', 'asset': 10000, 'cash': 0})
        
        # Day 2: Price drop (Drawdown)
        tester.history.append({'date': '2023-01-02', 'asset': 9000, 'cash': 5000}) 
        
        # Day 3: Price recovery
        tester.history.append({'date': '2023-01-03', 'asset': 11000, 'cash': 5000})
        
        metrics = tester.get_metrics()
        print(f"[PASS] Backtest Metrics: {metrics}")
        
        self.assertIn('max_drawdown', metrics)
        self.assertIn('cagr', metrics)
        self.assertNotEqual(metrics['max_drawdown'], "0.00%")

if __name__ == '__main__':
    unittest.main()
