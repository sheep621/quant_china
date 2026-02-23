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
from src.alpha_factory.factor_evaluator import FactorEvaluator, batch_evaluate_factors
from src.alpha_factory.orthogonalizer import Orthogonalizer, batch_filter_factors
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

# 配置
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(project_root, 'data', 'market_data.csv')
OUTPUT_DIR = os.path.join(project_root, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    """加载真实数据，如果不存在则自动下载（优先读取Parquet）"""
    import glob
    # 定位到位于项目根目录下的 data/raw
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "raw")
    files = glob.glob(os.path.join(data_dir, "*.parquet"))
    
    # 1. 优先读取已有的 Parquet 文件
    if files:
        logger.info(f"Loading {len(files)} real stocks data from {data_dir}...")
        df_list = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                df_list.append(df)
            except Exception:
                pass
        if df_list:
            full_df = pd.concat(df_list, ignore_index=True)
            if 'date' in full_df.columns:
                full_df['date'] = pd.to_datetime(full_df['date'])
            return full_df

    # 2. 如果没有读取到，尝试调用 DataLoader 下载沪深300作为真实数据源
    try:
        from src.data_engine.loader import DataLoader
        logger.warning(f"No existing parquet data found in {data_dir}! Calling DataLoader to fetch HS300 for real mining...")
        loader = DataLoader(data_dir=data_dir)
        if loader.login():
            from pandas.tseries.offsets import BDay
            start_ts = pd.Timestamp.now() - pd.Timedelta(days=365*3)
            # 必须退避到上一个工作日，否则周末/节假日 Baostock 无法拉取当天成分股
            start_date = (start_ts - BDay(1)).strftime("%Y-%m-%d")
            end_date = (pd.Timestamp.now() - BDay(1)).strftime("%Y-%m-%d")
            
            # 【致命漏洞修复：幸存者偏差】
            # 防止回测只盯着今天存活的好股票导致过度乐观。合并期初(三年前)和期末(今天)的成分股。
            codes_start = loader.get_stock_list(date=start_date)
            codes_end = loader.get_stock_list(date=end_date)
            
            # 集合去重并截取
            all_codes = list(set(codes_start + codes_end))
            target_codes = sorted(all_codes)[:200]
            
            logger.info(f"Downloading data for {len(target_codes)} stocks from {start_date} to {end_date}...")
            loader.update_data(target_codes, start_date, end_date)
            loader.logout()
            
            # 再试一次读取下载后的数据
            files = glob.glob(os.path.join(data_dir, "*.parquet"))
            df_list = []
            for f in files:
                try:
                    df = pd.read_parquet(f)
                    df_list.append(df)
                except Exception:
                    pass
            if df_list:
                full_df = pd.concat(df_list, ignore_index=True)
                if 'date' in full_df.columns:
                    full_df['date'] = pd.to_datetime(full_df['date'])
                return full_df
    except Exception as e:
        logger.error(f"Auto-download failed: {e}")

    # 3. 如果所有手段均失败，生成 Mock 数据兜底系统测试
    logger.warning("Data fallback failed! Generating MOCK data for system test...")
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
    # 将包含 NaN label 的行剔除，否则 GP 引擎会强行将它充当 0.0 给矿机拟合，形成噪音污染
    df_clean_mining = df_clean.dropna(subset=['label'])
    
    # 移除非特征列
    exclude_cols = ['date', 'code', 'label', 'next_open', 'next_2_open', 'is_limit_up', 'is_limit_down', 'next_is_limit_up', 'next_is_limit_down', 'next_2_is_limit_down', 'tradestatus', 'high_limit', 'limit_ratio']
    feature_cols = [c for c in df_clean_mining.columns if c not in exclude_cols]
    
    X = df_clean_mining[feature_cols]
    y = df_clean_mining['label']
    
    # 获取涨跌停掩码 (LULD Mask: 如果T+1天涨停买不到或者T+2天跌停卖不出，视为不可交易)
    # 【致命漏洞四修复】：基于时空平移的截获
    if 'next_is_limit_up' in df_clean_mining.columns and 'next_2_is_limit_down' in df_clean_mining.columns:
        luld_mask = df_clean_mining['next_is_limit_up'] | df_clean_mining['next_2_is_limit_down']
    else:
        luld_mask = pd.Series(False, index=df_clean_mining.index)
        
    # 基于日期 (而非单纯的行数) 构建无未来函数的训练/测试切分
    # 按照时间序列切出前 80% 的日期作为训练集
    unique_dates = df_clean_mining['date'].sort_values().unique()
    split_date_idx = int(len(unique_dates) * 0.8)
    if split_date_idx == 0:
        split_date = unique_dates[-1]  # 数据太少时 fallback
    else:
        split_date = unique_dates[split_date_idx]
        
    train_mask = df_clean_mining['date'] < split_date
    X_train = X[train_mask]
    y_train = y[train_mask]
    
    # 获取 codes, dates 和 luld_mask 供引擎隔离数据 (应用 train_mask)
    codes_train = df_clean_mining['code'][train_mask].values
    dates_train = df_clean_mining['date'][train_mask].values
    luld_train = luld_mask[train_mask]
    
    logger.info(f"Training Data: {X_train.shape}")

    
    # 2. Initialize Generator
    generator = AlphaGenerator(
        population_size=500, # 演示用小一点
        generations=5,
        n_jobs=1,
        warm_start=True,
        checkpoint_path=os.path.join(OUTPUT_DIR, 'population_checkpoint.pkl')
    )
    
    hall_of_fame = [] # 存放 (formula, fitness, metrics)
    factor_pool = pd.DataFrame()  # 已接受的因子池（用于正交性检查）
    
    # 初始化评估器和正交化器
    evaluator = FactorEvaluator()
    orthogonalizer = Orthogonalizer(method='incremental', threshold=0.7)
    
    # 3. Continuous Mining Loop
    # 3. Continuous Mining Loop
    current_iter = 0
    while True:
        if iterations != -1 and current_iter >= iterations:
            break
            
        current_iter += 1
        logger.info(f"--- Iteration {current_iter}/{'Infinite' if iterations == -1 else iterations} ---")
        
        # Fit (Warm Start enabled)
        # 支持传入 feature_names 及上下文以彻底隔离时序数据污染
        candidates = generator.fit(
            X_train, y_train, 
            feature_names=feature_cols, 
            codes=codes_train, 
            dates=dates_train
        )

        
        # 4. Evaluate & Filter with Quality Gates
        for idx, alpha in enumerate(candidates):
            formula = alpha['formula']
            fitness = alpha['fitness']
            
            # 简单去重（公式级别）
            if any(a['formula'] == formula for a in hall_of_fame):
                continue
            
            try:
                # 计算因子值 (传入 codes 和 dates 防数据污染)
                factor_values = generator.transform(
                    X_train,
                    codes=codes_train,
                    dates=dates_train
                )
                if factor_values.shape[1] <= idx:
                    continue
                factor_series = pd.Series(factor_values[:, idx], index=X_train.index)
                
                # 质量评估 (修复ICIR计算bug:透传dates及codes)
                metrics = evaluator.evaluate(
                    factor_series, 
                    y_train,
                    dates=dates_train,
                    codes=codes_train,
                    existing_factors=factor_pool,
                    luld_mask=luld_train
                )
                
                # 质量门控检查
                passed, reason = metrics.passes_quality_gate()
                
                if not passed:
                    logger.info(f"Alpha rejected: {formula[:50]}... | {reason}")
                    continue
                
                # 正交性检查
                if not factor_pool.empty:
                    is_unique, max_corr, most_similar = orthogonalizer.incremental_deduplication(
                        factor_series, factor_pool, dates=dates_train
                    )
                    if not is_unique:
                        logger.info(f"Alpha rejected (high correlation): {formula[:50]}...")
                        continue
                
                # 通过所有检查，加入Hall of Fame
                alpha_record = {
                    'formula': formula,
                    'fitness': fitness,
                    'ICIR': metrics.ICIR,
                    'IC_mean': metrics.IC_mean,
                    'sharpe': metrics.long_short_sharpe,
                    'uniqueness': metrics.factor_uniqueness
                }
                hall_of_fame.append(alpha_record)
                
                # 加入因子池
                factor_name = f"alpha_{len(hall_of_fame)}"
                factor_pool[factor_name] = factor_series
                
                logger.info(f"✓ New Alpha added: {formula[:50]}... | ICIR={metrics.ICIR:.3f}, Sharpe={metrics.long_short_sharpe:.2f}")
                
            except Exception as e:
                logger.warning(f"Evaluation failed for alpha: {str(e)}")
    
        # Save Results periodically (every iteration)
        output_file = os.path.join(OUTPUT_DIR, 'discovered_alphas.json')
        with open(output_file, 'w') as f:
            json.dump(hall_of_fame, f, indent=4)
        logger.info(f"Saved {len(hall_of_fame)} unique alphas to {output_file}")
        
        # 保存整个模型的记忆断点，用于下次增量挖掘
        generator.save_checkpoint()

    logger.info("Alpha Factory Stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Alpha Factory Continuous Runner')
    parser.add_argument('--iterations', type=int, default=3, help='Number of iterations to run (-1 for infinite)')
    args = parser.parse_args()
    
    run_alpha_factory(iterations=args.iterations)
