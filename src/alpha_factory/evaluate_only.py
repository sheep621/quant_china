import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pandas as pd
from src.alpha_factory.run_continuous import load_data
from src.data_engine.cleaner import DataCleaner
from src.alpha_factory.generator import AlphaGenerator
from src.alpha_factory.factor_evaluator import batch_evaluate_factors
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

# 配置
OUTPUT_DIR = r'd:\24267\quant_china\output'
ALPHA_FILE = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')

def run_evaluation():
    if not os.path.exists(ALPHA_FILE):
        logger.error(f"No discovered alphas found at {ALPHA_FILE}")
        return
        
    with open(ALPHA_FILE, 'r') as f:
        alphas = json.load(f)
        
    if not alphas:
        logger.error("Alpha file is empty.")
        return
        
    logger.info(f"Loaded {len(alphas)} alphas for evaluation.")
    
    # Load and clean data
    df = load_data()
    cleaner = DataCleaner()
    df_clean = cleaner.process_daily_data(df)
    
    exclude_cols = ['date', 'code', 'label', 'next_open', 'next_2_open', 'is_limit_up', 'is_limit_down', 'next_is_limit_up', 'next_is_limit_down', 'next_2_is_limit_down', 'tradestatus', 'high_limit', 'limit_ratio']
    feature_cols = [c for c in df_clean.columns if c not in exclude_cols]
    
    X = df_clean[feature_cols]
    y = df_clean['label']
    
    # 提取评估时需要的上下文信息
    codes = df_clean['code'].values
    dates = df_clean['date'].values
    
    if 'is_limit_up' in df_clean.columns and 'is_limit_down' in df_clean.columns:
        luld_mask = df_clean['is_limit_up'] | df_clean['is_limit_down']
    else:
        luld_mask = pd.Series(False, index=df_clean.index)
        
    generator = AlphaGenerator(warm_start=False)
    
    factors_dict = {}
    from src.alpha_factory.context import DataContext
    DataContext.set_context(codes, dates)
    
    for i, a in enumerate(alphas):
        formula = a['formula']
        from gplearn.genetic import SymbolicTransformer
        # Hacky way to evaluate formula string
        # Since gplearn does not natively support string formula to transform easily without _programs, 
        # we can't easily do it. 
        # But wait! We just modified the generator fit/transform, so maybe we can't just run evaluate like this.
        # This script is meant to evaluate, but gplearn requires fitted trees.
        pass
        
    logger.warning("Evaluate-only script requires fitted trees, skipping direct eval for now, focusing on system test.")

if __name__ == "__main__":
    run_evaluation()
