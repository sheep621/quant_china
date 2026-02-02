import os
import sys
# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
import pandas as pd
import numpy as np
import json
from src.alpha_factory.generator import AlphaGenerator
from src.data_engine.cleaner import DataCleaner
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

# 配置
DATA_PATH = r'd:\24267\quant_china\data\market_data.csv' # 假设数据路径
OUTPUT_DIR = r'd:\24267\quant_china\output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    """加载数据，如果不存在则生成Mock数据用于测试"""
    if os.path.exists(DATA_PATH):
        logger.info(f"Loading data from {DATA_PATH}")
        df = pd.read_csv(DATA_PATH)
        # 确保日期格式
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        return df
    else:
        logger.warning("Data file not found, generating MOCK data for system test...")
        dates = pd.date_range(start='2023-01-01', periods=100)
        codes = [f'sh.600{i:03d}' for i in range(10)]
        data = []
        for date in dates:
            for code in codes:
                row = {
                    'date': date,
                    'code': code,
                    'open': 10 + np.random.randn(),
                    'close': 10 + np.random.randn(),
                    'high': 11 + np.random.randn(),
                    'low': 9 + np.random.randn(),
                    'volume': 1000 + abs(np.random.randn() * 100),
                    'amount': 10000 + abs(np.random.randn() * 1000),
                    'preClose': 10.0,
                    'pctChg': np.random.randn() * 0.05,
                    'turn': np.random.rand() * 0.1,
                    'isST': 0,
                    'tradestatus': '1'
                }
                data.append(row)
        return pd.DataFrame(data)

def orthogonality_check(new_alpha_scores, existing_alphas_scores, threshold=0.7):
    """
    正交性/相关性检查 (简化版Löwdin思想: 剔除高相关)
    new_alpha_scores: Series (Time Index)
    existing_alphas_scores: DataFrame (Cols=Alphas)
    """
    if existing_alphas_scores.empty:
        return True
    
    # 计算相关性
    # 假设这里传入的是因子值(Scores)
    corrs = existing_alphas_scores.corrwith(new_alpha_scores, axis=0)
    max_corr = corrs.abs().max()
    
    if max_corr > threshold:
        logger.info(f"Alpha rejected due to high correlation: {max_corr:.2f}")
        return False
    return True

def run_alpha_factory(iterations=3):
    """
    Alpha 挖掘主循环 (Factory Loop)
    """
    logger.info("Starting Alpha Factory...")
    
    # 1. Load & Clean Data
    df = load_data()
    cleaner = DataCleaner()
    df_clean = cleaner.process_daily_data(df)
    
    # 准备特征 X 和标签 y
    # 移除非特征列
    exclude_cols = ['date', 'code', 'label', 'next_open', 'next_2_open', 'is_limit_up', 'is_limit_down', 'tradestatus']
    feature_cols = [c for c in df_clean.columns if c not in exclude_cols]
    
    X = df_clean[feature_cols]
    y = df_clean['label']
    
    # 简单的 train/test split (滚动训练逻辑可在外层做, 这里演示单次)
    # 假设最后20%做验证
    split_idx = int(len(df_clean) * 0.8)
    X_train, y_train = X.iloc[:split_idx], y.iloc[:split_idx]
    
    logger.info(f"Training Data: {X_train.shape}")
    
    # 2. Initialize Generator
    generator = AlphaGenerator(
        population_size=500, # 演示用小一点
        generations=5,
        n_jobs=1,
        warm_start=True
    )
    
    hall_of_fame = [] # 存放 (formula, fitness)
    
    # 3. Continuous Mining Loop
    # 3. Continuous Mining Loop
    current_iter = 0
    while True:
        if iterations != -1 and current_iter >= iterations:
            break
            
        current_iter += 1
        logger.info(f"--- Iteration {current_iter}/{'Infinite' if iterations == -1 else iterations} ---")
        
        # Fit (Warm Start enabled)
        # 支持传入 feature_names 方便生成公式可读
        candidates = generator.fit(X_train, y_train, feature_names=feature_cols)
        
        # 4. Filter & Save
        for alpha in candidates:
            formula = alpha['formula']
            fitness = alpha['fitness']
            
            # 这里应进行正交性检查 (需要 transform 计算因子值)
            # 为节省时间, 仅演示逻辑
            # scores = generator.transform(X_train, formula) 
            # if orthogonality_check(scores, existing_scores): ...
            
            # 简单去重
            if not any(a['formula'] == formula for a in hall_of_fame):
                hall_of_fame.append(alpha)
                logger.info(f"New Alpha added to Hall of Fame: {formula}")
    
        # Save Results periodically (every iteration)
        output_file = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')
        with open(output_file, 'w') as f:
            json.dump(hall_of_fame, f, indent=4)
        logger.info(f"Saved {len(hall_of_fame)} unique alphas to {output_file}")
            
    logger.info("Alpha Factory Stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Alpha Factory Continuous Runner')
    parser.add_argument('--iterations', type=int, default=3, help='Number of iterations to run (-1 for infinite)')
    args = parser.parse_args()
    
    run_alpha_factory(iterations=args.iterations)
