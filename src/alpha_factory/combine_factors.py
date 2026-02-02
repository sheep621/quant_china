import os
import sys
# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pandas as pd
import numpy as np
import lightgbm as lgb
from src.infrastructure.logger import get_system_logger
from src.alpha_factory.run_continuous import load_data
from src.data_engine.cleaner import DataCleaner
from src.model_layer.lgbm_trainer import LGBMTrainer
# Import operators to register them for eval
from src.alpha_factory.operators import *

logger = get_system_logger()

OUTPUT_DIR = r'd:\24267\quant_china\output'
ALPHA_FILE = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')

def load_alphas():
    if not os.path.exists(ALPHA_FILE):
        logger.error(f"Alpha file not found: {ALPHA_FILE}")
        return []
    with open(ALPHA_FILE, 'r') as f:
        return json.load(f)

def evaluate_formula(formula, context):
    """
    Evaluate a formula string within a context (DataFrame columns/Operators).
    This is a simplified evaluator using python's eval().
    We map gplearn function names to actual python functions in context.
    
    WARNING: eval() is unsafe with untrusted input. Ensure alphas are from trusted source.
    """
    # Mapping gplearn names (e.g. 'add', 'tsrank5') to python functions
    # Most gplearn base functions are available in numpy (add, sub, mul, etc)
    # Custom operators are imported from operators.py
    
    # We need to construct a safe evaluation environment
    safe_dict = {
        'add': np.add, 'sub': np.subtract, 'mul': np.multiply, 'div': protected_div,
        'neg': np.negative, 'abs': np.abs, 'log': protected_log, 'sqrt': protected_sqrt,
        'signpow': signed_power,
        
        'tsrank5': ts_rank_5, 'tsrank10': ts_rank_10, 
        'decay5': decay_linear_5, 'decay10': decay_linear_10,
        'tsmin5': ts_min_5, 'tsmax5': ts_max_5, 
        'tsargmax5': ts_argmax_5, 'tsargmin5': ts_argmin_5,
        'tssum5': ts_sum_5, 'tsstd5': ts_stddev_5,
        'delay1': ts_delay_1, 'delay5': ts_delay_5, 'delta1': ts_delta_1,
        'skew5': ts_skewness_5, 'kurt5': ts_kurtosis_5, 'mad5': ts_mad_5,
        
        'rank': rank, 'scale': scale, 'trunc': truncate, 'indneu': ind_neutralize,
        
        'if': condition, 'abs': abs_val, 'limdist': limit_distance,
        
        'corr5': correlation_5, 'cov5': covariance_5
    }
    
    # Add dataframe columns as variables
    # context is a dict of {col_name: np.array}
    eval_context = safe_dict.copy()
    eval_context.update(context)
    
    try:
        # gplearn formulas look like: add(mul(close, open), log(volume))
        # This is valid python syntax if functions are defined.
        return eval(formula, {"__builtins__": {}}, eval_context)
    except Exception as e:
        logger.warning(f"Failed to evaluate formula: {formula} | Error: {e}")
        return None

def main():
    logger.info("Starting Factor Combination...")
    
    # 1. Load Alphas
    alphas = load_alphas()
    if not alphas:
        logger.warning("No alphas found to combine.")
        return

    logger.info(f"Loaded {len(alphas)} alphas.")
    
    # 2. Load Data
    df = load_data()
    cleaner = DataCleaner()
    df_clean = cleaner.process_daily_data(df)
    
    # Prepare context for evaluation (arrays)
    # All columns in df become variables
    context = {col: df_clean[col].values for col in df_clean.columns}
    
    # 3. Construct Factor Matrix
    factor_data = {}
    valid_alphas = []
    
    for i, alpha in enumerate(alphas):
        formula = alpha['formula']
        res = evaluate_formula(formula, context)
        if res is not None:
             # Ensure length matches
             if len(res) == len(df_clean):
                 name = f"alpha_{i}"
                 factor_data[name] = res
                 valid_alphas.append(name)
             else:
                 logger.warning(f"Alpha {i} dimension mismatch: {len(res)} vs {len(df_clean)}")

    if not factor_data:
        logger.error("No valid factors generated.")
        return

    df_factors = pd.DataFrame(factor_data)
    # Combine with original DF to track date/label
    df_final = pd.concat([df_clean[['date', 'label']].reset_index(drop=True), df_factors], axis=1)
    
    # Drop rows with NaNs (factors might introduce NaNs at start)
    df_final.dropna(inplace=True)
    
    logger.info(f"Factor Matrix Created: {df_final.shape}")
    
    # 4. Train LightGBM
    trainer = LGBMTrainer()
    
    # Split Train/Val (Simple time split)
    split_idx = int(len(df_final) * 0.8)
    df_train = df_final.iloc[:split_idx]
    df_val = df_final.iloc[split_idx:]
    
    features = valid_alphas
    label = 'label'
    
    logger.info("Training Ensemble Model...")
    model = trainer.train(df_train, features, label, df_val)
    
    # 5. Evaluate
    if model:
        logger.info("Feature Importance:")
        imp = trainer.get_feature_importance()
        sorted_imp = sorted(imp.items(), key=lambda x: x[1], reverse=True)[:10]
        for name, val in sorted_imp:
            logger.info(f"  {name}: {val}")
            
    logger.info("Factor Combination Completed.")

if __name__ == "__main__":
    main()
