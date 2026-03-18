"""
非线性 AI 因子合成器 (LightGBM Factor Synthesis)
=================================================
本模块承担以下职责：

1. 加载 discovered_alphas.json 中所有已通过质量门控的因子公式
2. 重新在全量数据上计算各因子的截面值，构建"超因子矩阵"
3. 训练一个 LightGBM 排序模型 (regressor / ranker) 作为非线性合成器
4. 将模型输出 (打分) 用于每日股票排名 —— 代替原来的简单线性加权求和

核心思想: 让 AI 自己学习在不同市场状态下，哪些 Alpha 因子对未来收益更有预测力，
并以非线性交互方式加权合成，而不是固定的线性组合。
"""

import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

import json
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from typing import Optional, List

from src.infrastructure.logger import get_system_logger
from src.alpha_factory.run_continuous import load_data
from src.data_engine.cleaner import DataCleaner
from src.alpha_factory.context import DataContext

logger = get_system_logger()

OUTPUT_DIR = os.path.join(project_root, 'output')
ALPHA_FILE = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')
MODEL_PATH = os.path.join(OUTPUT_DIR, 'lgbm_synthesizer.pkl')


# ─────────────────────────────────────────────
#  通用工具：从公式字符串计算因子值
# ─────────────────────────────────────────────

def _build_eval_context(df: pd.DataFrame, feature_cols: List[str]) -> dict:
    """构建 eval() 的安全命名空间，映射列名和 X0/X1/... 索引。"""
    from src.alpha_factory.operators import custom_operations
    ctx = {
        'add': np.add, 'sub': np.subtract, 'mul': np.multiply,
        'neg': np.negative, 'abs': np.abs, 'log': np.log,
        'sqrt': np.sqrt, 'min': np.minimum, 'max': np.maximum,
        'sign': np.sign,
    }
    for op in custom_operations:
        ctx[op.name] = op.function
    for col in df.columns:
        ctx[col] = df[col].values
    for i, col in enumerate(feature_cols):
        ctx[f'X{i}'] = df[col].values
    return ctx


def evaluate_formula(formula: str, ctx: dict) -> Optional[np.ndarray]:
    """安全执行因子公式，失败时返回 None。"""
    try:
        result = eval(formula, {"__builtins__": {}}, ctx)
        if isinstance(result, (int, float)):
            result = np.full(len(next(iter(ctx.values()))), float(result))
        arr = np.array(result, dtype=np.float64)
        arr = np.where(np.isfinite(arr), arr, np.nan)
        return arr
    except Exception as e:
        logger.debug(f"Formula eval failed: {formula[:40]}... | {e}")
        return None


# ─────────────────────────────────────────────
#  构建超因子矩阵 (Alpha Factor Matrix)
# ─────────────────────────────────────────────

def build_factor_matrix(df_clean: pd.DataFrame, alphas: list) -> pd.DataFrame:
    """
    在完整历史数据上计算每个 Alpha 的截面值，返回对齐的 DataFrame。
    列名为 alpha_0, alpha_1, ...
    """
    exclude_cols = [
        'date', 'code', 'label', 'next_open', 'next_2_open',
        'is_limit_up', 'is_limit_down', 'next_is_limit_up',
        'next_is_limit_down', 'next_2_is_limit_down',
        'tradestatus', 'high_limit', 'limit_ratio'
    ]
    feature_cols = [c for c in df_clean.columns if c not in exclude_cols]

    # 设置上下文（防止算子跨股票泄露）
    DataContext.set_context(df_clean['code'].values, df_clean['date'].values)
    ctx = _build_eval_context(df_clean, feature_cols)

    factor_cols = {}
    n = len(df_clean)

    for i, alpha in enumerate(alphas):
        formula = alpha.get('formula', '')
        if not formula:
            continue
        result = evaluate_formula(formula, ctx)
        if result is not None and len(result) == n:
            factor_cols[f'alpha_{i}'] = result

    if not factor_cols:
        return pd.DataFrame()

    df_factors = pd.DataFrame(factor_cols, index=df_clean.index)
    return df_factors


# ─────────────────────────────────────────────
#  LightGBM 合成器训练
# ─────────────────────────────────────────────

LGBM_PARAMS = {
    'objective': 'regression',
    'metric': 'rmse',
    'learning_rate': 0.05,
    'num_leaves': 63,
    'max_depth': 6,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_child_samples': 30,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'verbose': -1,
    'n_jobs': -1,
}

NUM_BOOST_ROUND = 300
EARLY_STOPPING_ROUNDS = 30


def train_synthesizer(
    df_clean: pd.DataFrame,
    df_factors: pd.DataFrame,
    model_path: str = MODEL_PATH,
) -> Optional[lgb.Booster]:
    """
    训练 LightGBM 合成器。

    输入: 因子截面值矩阵 (n_samples × n_factors) + 目标 label
    输出: 保存的 LightGBM Booster 模型
    """
    if df_factors.empty:
        logger.error("Factor matrix is empty, cannot train synthesizer.")
        return None

    label = df_clean['label'].values
    features = df_factors.columns.tolist()

    # 按时间切分
    unique_dates = np.sort(df_clean['date'].unique())
    split_date = unique_dates[int(len(unique_dates) * 0.8)]
    train_mask = df_clean['date'] < split_date
    val_mask = ~train_mask

    X_train = df_factors.loc[train_mask, features]
    y_train = label[train_mask]
    X_val = df_factors.loc[val_mask, features]
    y_val = label[val_mask]

    # 过滤 NaN
    train_valid = np.isfinite(y_train) & X_train.notna().all(axis=1)
    val_valid = np.isfinite(y_val) & X_val.notna().all(axis=1)

    if train_valid.sum() < 100:
        logger.warning("Too few valid training samples, skipping synthesizer training.")
        return None

    dtrain = lgb.Dataset(X_train[train_valid], label=y_train[train_valid])
    dval = lgb.Dataset(X_val[val_valid], label=y_val[val_valid], reference=dtrain)

    logger.info(f"Training LightGBM synthesizer | train={train_valid.sum()}, val={val_valid.sum()}, features={len(features)}")

    callbacks = [
        lgb.early_stopping(stopping_rounds=EARLY_STOPPING_ROUNDS, verbose=False),
        lgb.log_evaluation(period=50),
    ]

    model = lgb.train(
        LGBM_PARAMS,
        dtrain,
        num_boost_round=NUM_BOOST_ROUND,
        valid_sets=[dval],
        callbacks=callbacks,
    )

    # 持久化
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"Synthesizer model saved to {model_path} | best_iteration={model.best_iteration}")

    # 打印 Top 10 特征重要性
    importance = model.feature_importance(importance_type='gain')
    feat_imp = sorted(zip(features, importance), key=lambda x: -x[1])
    logger.info("Top Feature Importances:")
    for fname, imp in feat_imp[:10]:
        logger.info(f"  {fname}: {imp:.2f}")

    return model


def load_synthesizer(model_path: str = MODEL_PATH) -> Optional[lgb.Booster]:
    """加载已保存的合成器模型。"""
    if not os.path.exists(model_path):
        return None
    try:
        model = joblib.load(model_path)
        logger.info(f"Synthesizer model loaded from {model_path}")
        return model
    except Exception as e:
        logger.warning(f"Failed to load synthesizer: {e}")
        return None


def score_stocks(model: lgb.Booster, df_factors: pd.DataFrame) -> pd.Series:
    """
    用 LightGBM 给一个截面打分，返回每只股票的合成 Alpha 得分。
    得分越高 → 预测收益率越高 → 越值得买入。
    """
    features = model.feature_name()
    # 只保留模型训练时使用的列
    available = [f for f in features if f in df_factors.columns]
    X = df_factors[available].copy()

    # 缺失的列补 0
    for f in features:
        if f not in X.columns:
            X[f] = 0.0

    X = X[features]
    scores = model.predict(X.values, num_iteration=model.best_iteration)
    return pd.Series(scores, index=df_factors.index, name='lgbm_score')


# ─────────────────────────────────────────────
#  主入口
# ─────────────────────────────────────────────

def main():
    logger.info("=== Combining Factors with LightGBM Synthesizer ===")

    # 1. 加载因子
    if not os.path.exists(ALPHA_FILE):
        logger.error(f"Alpha file not found: {ALPHA_FILE}")
        return
    with open(ALPHA_FILE) as f:
        alphas = json.load(f)
    if not alphas:
        logger.warning("No alphas found. Please run the alpha factory first.")
        return
    logger.info(f"Loaded {len(alphas)} discovered alphas.")

    # 2. 加载数据
    df_raw = load_data()
    cleaner = DataCleaner()
    df_clean = cleaner.process_daily_data(df_raw)

    # 3. 构建因子矩阵
    df_factors = build_factor_matrix(df_clean, alphas)
    if df_factors.empty:
        logger.error("Factor matrix empty after evaluation.")
        return

    # 4. 训练合成器
    model = train_synthesizer(df_clean, df_factors)
    if model is None:
        logger.error("Synthesizer training failed.")
        return

    logger.info("=== LightGBM Synthesizer Training Complete ===")


if __name__ == '__main__':
    main()
