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
    # 致命架构缺陷修复：废弃硬编码字典，动态全量挂载自 _operators 中的所有防护版算子
    from src.alpha_factory.operators import custom_operations
    safe_dict = {
        'add': np.add, 'sub': np.subtract, 'mul': np.multiply,
        'neg': np.negative, 'abs': np.abs
    }
    for op in custom_operations:
        safe_dict[op.name] = op.function
    
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
    
    # 致命架构缺陷修复：必须在评价前全局装载时空掩码上下文，否则所有的截面/时序算子将在复盘计算时全量穿透股票隔离屏障！
    from src.alpha_factory.context import DataContext
    DataContext.set_context(df_clean['code'].values, df_clean['date'].values)
    
    # Prepare context for evaluation (arrays)
    # All columns in df become variables
    context = {col: df_clean[col].values for col in df_clean.columns}
    
    # Also map X0, X1... to feature columns to support gplearn default names
    # We must use the same logic as run_continuous.py to determine feature columns
    # We must use the same logic as run_continuous.py to determine feature columns
    exclude_cols = ['date', 'code', 'label', 'next_open', 'next_2_open', 'is_limit_up', 'is_limit_down', 'next_is_limit_up', 'next_is_limit_down', 'next_2_is_limit_down', 'tradestatus', 'high_limit', 'limit_ratio']
    feature_cols = [c for c in df_clean.columns if c not in exclude_cols]
    
    for i, col in enumerate(feature_cols):
        context[f'X{i}'] = df_clean[col].values
    
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
