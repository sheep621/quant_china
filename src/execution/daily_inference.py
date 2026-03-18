"""
每日选股推理引擎 (Daily Alpha Inference & Stock Picker)
=====================================================
本脚本承担以下职责：

1. 加载已发现的 Alpha 因子及历史市场数据
2. 计算当天各股票在每个因子上的截面值
3. 优先使用 LightGBM 非线性合成器打分（如果模型存在）
   fallback 降级至 Z-Score + IC 加权线性求和打分
4. 过滤停牌、涨停板股票
5. 输出前 5 名最高得分的买入推荐

运行方式:
    python src/execution/daily_inference.py
    
可选参数:
    --top  N        输出前 N 名（默认 5）
    --train-model   运行前先训练/更新 LightGBM 合成器
"""

import os
import sys
import json
import argparse
import logging
import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.infrastructure.logger import get_system_logger
from src.alpha_factory.run_continuous import load_data
from src.data_engine.cleaner import DataCleaner
from src.alpha_factory.operators import custom_operations
from src.alpha_factory.context import DataContext

logger = get_system_logger()

OUTPUT_DIR = os.path.join(project_root, 'output')
ALPHA_FILE  = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')
MODEL_PATH  = os.path.join(OUTPUT_DIR, 'lgbm_synthesizer.pkl')

EXCLUDE_COLS = [
    'date', 'code', 'label', 'next_open', 'next_2_open',
    'is_limit_up', 'is_limit_down', 'next_is_limit_up',
    'next_is_limit_down', 'next_2_is_limit_down',
    'tradestatus', 'high_limit', 'limit_ratio'
]


# ──────────────────────────────────────────────────────
#  工具函数
# ──────────────────────────────────────────────────────

def load_alphas():
    """
    加载高质量 alpha，返回 [(formula, weight), ...]
    
    来源优先级：
    1. wq101_factors.py —— 80+ 个经典因子，随时可用（权重=1.0）
    2. discovered_alphas.json —— GP 挖掘出的新因子，按 ICIR 加权（如果存在）
    """
    alphas = []

    # ── 来源 1：Alpha 101 经典因子（永远可用）──
    try:
        from src.alpha_factory.wq101_factors import WQ101_ALPHAS
        for a in WQ101_ALPHAS:
            formula = a.get('formula', '')
            if formula:
                alphas.append((formula, 1.0))  # 经典因子权重统一设为 1.0
        logger.info(f"Loaded {len(WQ101_ALPHAS)} classic Alpha101 factors from wq101_factors.py")
    except Exception as e:
        logger.warning(f"Failed to load WQ101 factors: {e}")

    # ── 来源 2：GP 发现的新因子（如果有）──
    if os.path.exists(ALPHA_FILE):
        try:
            with open(ALPHA_FILE) as f:
                discovered = json.load(f)
            n_before = len(alphas)
            for a in discovered:
                weight = a.get('ICIR', a.get('fitness', 1.0))
                if weight > 0 and a.get('formula'):
                    alphas.append((a['formula'], weight * 2.0))  # GP 因子给双倍权重奖励
            logger.info(f"Merged {len(alphas) - n_before} GP-discovered factors from {ALPHA_FILE}")
        except Exception as e:
            logger.warning(f"Failed to load discovered alphas: {e}")

    if not alphas:
        logger.error("No factors found from any source!")
    else:
        logger.info(f"Total factors for inference: {len(alphas)}")

    return alphas



def build_eval_context(df: pd.DataFrame, feature_cols: list) -> dict:
    """构建安全 eval 命名空间，映射列名 + 算子 + X0/X1 索引。"""
    ctx = {
        'add': np.add, 'sub': np.subtract, 'mul': np.multiply,
        'neg': np.negative, 'abs': np.abs, 'if': np.where,
        'log': np.log, 'sqrt': np.sqrt, 'sign': np.sign,
        'min': np.minimum, 'max': np.maximum,
    }
    for op in custom_operations:
        ctx[op.name] = op.function
    for col in df.columns:
        ctx[col] = df[col].values
    for i, col in enumerate(feature_cols):
        ctx[f'X{i}'] = df[col].values
    return ctx


def evaluate_formula(formula: str, ctx: dict) -> np.ndarray | None:
    """安全执行因子公式。"""
    try:
        result = eval(formula, {"__builtins__": {}}, ctx)
        arr = np.array(result, dtype=np.float64)
        return np.where(np.isfinite(arr), arr, np.nan)
    except Exception as e:
        logger.debug(f"Formula eval failed: {formula[:40]}... | {e}")
        return None


# ──────────────────────────────────────────────────────
#  打分引擎
# ──────────────────────────────────────────────────────

def score_with_lgbm(df_clean: pd.DataFrame, alphas_with_weights: list) -> pd.Series | None:
    """
    使用已保存的 LightGBM 合成器打分。
    如果模型文件不存在，返回 None，降级至线性打分。
    """
    import joblib
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        logger.warning(f"[LGBM] Failed to load synthesizer: {e}")
        return None

    feature_cols = [c for c in df_clean.columns if c not in EXCLUDE_COLS]
    DataContext.set_context(df_clean['code'].values, df_clean['date'].values)
    ctx = build_eval_context(df_clean, feature_cols)

    feature_names = model.feature_name()
    factor_dict = {}

    for name in feature_names:
        # feature 名称形如 'alpha_0', 对应第 N 个 alpha 的公式
        try:
            idx = int(name.split('_')[1])
            formula, _ = alphas_with_weights[idx]
            result = evaluate_formula(formula, ctx)
            if result is not None and len(result) == len(df_clean):
                factor_dict[name] = result
            else:
                factor_dict[name] = np.zeros(len(df_clean))
        except Exception:
            factor_dict[name] = np.zeros(len(df_clean))

    X = pd.DataFrame(factor_dict)[feature_names]
    scores = model.predict(X.values, num_iteration=model.best_iteration)
    logger.info(f"[LGBM] Scored {len(scores)} rows with synthesizer model.")
    return pd.Series(scores, index=df_clean.index, name='score')


def score_with_linear(df_clean: pd.DataFrame, alphas_with_weights: list) -> pd.Series:
    """
    降级策略：Z-Score 标准化后的 IC 加权线性求和。
    """
    feature_cols = [c for c in df_clean.columns if c not in EXCLUDE_COLS]
    DataContext.set_context(df_clean['code'].values, df_clean['date'].values)
    ctx = build_eval_context(df_clean, feature_cols)

    composite = np.zeros(len(df_clean))
    total_weight = 0.0
    valid_count = 0

    for formula, weight in alphas_with_weights:
        res = evaluate_formula(formula, ctx)
        if res is None or len(res) != len(df_clean):
            continue
        res = np.nan_to_num(res, posinf=0.0, neginf=0.0)
        std = np.std(res)
        if std > 1e-5:
            res_norm = (res - np.mean(res)) / std
            composite += res_norm * weight
            total_weight += weight
            valid_count += 1

    if total_weight > 0:
        composite /= total_weight

    logger.info(f"[Linear] Scored using {valid_count}/{len(alphas_with_weights)} valid factors.")
    return pd.Series(composite, index=df_clean.index, name='score')


# ──────────────────────────────────────────────────────
#  主函数
# ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Daily Alpha Inference & Stock Picker')
    parser.add_argument('--top', type=int, default=5, help='Number of top stocks to output')
    parser.add_argument('--train-model', action='store_true',
                        help='Train/update LightGBM synthesizer before inference')
    args = parser.parse_args()

    logger.info("=" * 53)
    logger.info("   Daily Alpha Inference & AI Stock Selector   ")
    logger.info("=" * 53)

    # ── 可选：先训练/更新 LGBM ──
    if args.train_model:
        logger.info("[Step 0] Training LightGBM synthesizer first...")
        try:
            from src.alpha_factory.combine_factors import main as train_main
            train_main()
        except Exception as e:
            logger.warning(f"Synthesizer training failed (non-fatal): {e}")

    # ── Step 1: 加载 Alpha ──
    alphas_with_weights = load_alphas()
    if not alphas_with_weights:
        logger.error("No valid alphas found. Please run the Alpha Factory first.")
        return
    logger.info(f"Loaded {len(alphas_with_weights)} quality alphas for inference.")

    # ── Step 2: 加载 & 清洗数据 ──
    logger.info("Loading market data...")
    df_raw = load_data()
    if df_raw is None or df_raw.empty:
        logger.error("Failed to load market data.")
        return
    cleaner = DataCleaner()
    df_clean = cleaner.process_daily_data(df_raw)
    if df_clean is None or df_clean.empty:
        logger.error("Data processing resulted in empty dataframe.")
        return

    latest_date = df_clean['date'].max()
    logger.info(f"Latest trading date in dataset: {latest_date.strftime('%Y-%m-%d')}")

    # ── Step 3: 打分（LGBM 优先，降级线性）──
    logger.info("Scoring stocks...")
    scores = score_with_lgbm(df_clean, alphas_with_weights)
    if scores is None:
        logger.info("[LGBM] No synthesizer model found — using linear scoring fallback.")
        scores = score_with_linear(df_clean, alphas_with_weights)
    df_clean['score'] = scores

    # ── Step 4: 取最新交易日快照 & 过滤不可交易标的 ──
    df_latest = df_clean[df_clean['date'] == latest_date].copy()
    df_latest['score'] = df_clean.loc[df_clean['date'] == latest_date, 'score'].values

    if 'tradestatus' in df_latest.columns:
        df_latest = df_latest[df_latest['tradestatus'] == '1']
    if 'is_limit_up' in df_latest.columns:
        df_latest = df_latest[~df_latest['is_limit_up'].astype(bool)]

    df_latest = df_latest.dropna(subset=['score'])

    # ── Step 5: 输出 Top N ──
    top_n = df_latest.sort_values(by='score', ascending=False).head(args.top)

    scorer_used = "🤖 LightGBM AI" if os.path.exists(MODEL_PATH) else "📐 Linear IC Weighted"
    logger.info(f"\n{'='*53}")
    logger.info(f"  🌟 TOP {args.top} BUY RECOMMENDATIONS (Scoring: {scorer_used})  ")
    logger.info(f"{'='*53}")
    logger.info(f"  {'#':<3} {'Code':<14} {'Score':>8}   {'Last Close':>12}")
    logger.info(f"  {'─'*50}")
    for rank, (_, row) in enumerate(top_n.iterrows(), 1):
        code  = row.get('code', 'N/A')
        score = row.get('score', 0.0)
        close = row.get('close', 'N/A')
        close_str = f"{close:>10.2f}" if isinstance(close, (int, float)) else str(close)
        logger.info(f"  {rank:<3} {code:<14} {score:>8.4f}   {close_str}")
    logger.info(f"{'='*53}\n")


if __name__ == '__main__':
    main()
