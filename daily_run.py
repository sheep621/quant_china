import pandas as pd
import numpy as np
import os
import joblib
import lightgbm as lgb
from datetime import datetime
from src.infrastructure.logger import get_system_logger
from src.data_engine.loader import DataLoader
from src.data_engine.cleaner import DataCleaner

logger = get_system_logger()

# === 每日运行流水线 (Production Workflow) ===
def run_daily_trading():
    logger.info("=== 启动每日实盘预测引擎 (Daily Production Engine) ===")
    
    # 1. 检查模型是否准备就绪
    ckpt_dir = "data/checkpoint"
    gen_path = f"{ckpt_dir}/alpha_generator.pkl"
    lgb_path = f"{ckpt_dir}/lgbm_model.txt"
    feat_path = f"{ckpt_dir}/feature_cols.pkl"
    base_feat_path = f"{ckpt_dir}/base_features.pkl"
    
    if not all(os.path.exists(p) for p in [gen_path, lgb_path, feat_path, base_feat_path]):
        logger.error("🛑 未找到固化的模型文件。请先运行 `python run_pipeline.py` 进行全量回测与模型存盘！")
        return

    # 加载模型
    logger.info("📦 加载最新固化的遗传因子挖掘器与 Lambdarank 模型...")
    generator = joblib.load(gen_path)
    model = lgb.Booster(model_file=lgb_path)
    features = joblib.load(feat_path)
    base_features = joblib.load(base_feat_path)
    
    # 2. 自动增量抓取最新行情
    logger.info("📡 Step 1: 扫描并增量同步全市场最新日线数据...")
    loader = DataLoader()
    loader.sync_all() 
    
    # 3. 提取最近的温床快照（60天）供时序特征计算
    logger.info("🧮 Step 2: 组装截面快照与特征计算引擎...")
    cleaner = DataCleaner()
    data_dir = "data/raw"
    import glob
    files = glob.glob(f"{data_dir}/*.parquet")
    
    all_dfs = []
    for f in files:
        df = pd.read_parquet(f)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # 仅截取近 60 天减轻内存负担，保证窗口函数能推算
            df = df.sort_values('date').tail(60)
            all_dfs.append(df)
            
    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df = cleaner.process_daily_data(full_df)
    
    # 4. 生成 Alpha 特征
    logger.info("🧬 Step 3: 通过 Genetic Programming 公式全自动生成 Alpha 因子...")
    # 注意：为了让模型生成最新的截面数据，我们需要对最新的那几天数据做 transform
    codes_arr = full_df['code'].values
    dates_arr = full_df['date'].values
    
    new_alphas = generator.transform(full_df[base_features], codes=codes_arr, dates=dates_arr)
    new_alpha_cols = [f"alpha_{i}" for i in range(new_alphas.shape[1])]
    df_alphas = pd.DataFrame(new_alphas, columns=new_alpha_cols, index=full_df.index)
    df_enriched = pd.concat([full_df, df_alphas], axis=1)
    
    # 截面特征标准化（与 run_pipeline 必须一字不落保持一致）
    features_to_normalize = base_features + new_alpha_cols
    grouped = df_enriched.groupby('date')[features_to_normalize]
    mean_df = grouped.transform('mean')
    std_df = grouped.transform('std')
    df_enriched[features_to_normalize] = (df_enriched[features_to_normalize] - mean_df) / (std_df + 1e-8)
    
    # 5. 生成明日调仓指令
    last_date = df_enriched['date'].max()
    logger.info(f"🎯 Step 4: 根据最新交易日 {last_date.date()} 截面提取明日信号...")
    
    daily_slice = df_enriched[df_enriched['date'] == last_date].copy()
    if daily_slice.empty:
        logger.error("🛑 当日数据截面为空！")
        return
        
    # 剔除一字板、停牌，或者连最低成交额要求都没达到的极度不活跃股（已经在 Universe 里筛掉一部分了）
    # 这里用是否产生 label 且未被风控阻拦为准
    daily_slice = daily_slice.dropna(subset=features)
    
    logger.info("🧠 模型进行 Lambdarank 高维并行打分排序...")
    preds = model.predict(daily_slice[features].values, num_iteration=model.best_iteration)
    daily_slice['rank_score'] = preds
    
    # 取 Top 10
    top10_slice = daily_slice.sort_values('rank_score', ascending=False).head(10)
    top10_codes = top10_slice['code'].tolist()
    
    # 6. 计算协方差与风险平价权重 (Risk Parity Weights)
    logger.info("⚖️ 正在提取近期波动率并求解 Risk Parity (等风险贡献) 最优仓位权重...")
    from scipy.optimize import minimize
    import warnings
    warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    # 从已经加载的 60 天底表中提取这 10 只股票的收盘价
    hist_slice = full_df[full_df['code'].isin(top10_codes)].copy()
    price_pivot = hist_slice.pivot(index='date', columns='code', values='close')
    
    # 计算日收益率并取最近 20 或 30 天样本
    returns_df = price_pivot.pct_change().dropna().tail(30)
    
    # 如果遇到停牌导致收益率为 0，施加微弱噪音防止协方差矩阵奇异(Singular)
    for c in returns_df.columns:
        if returns_df[c].std() == 0:
            returns_df[c] += np.random.normal(0, 1e-6, len(returns_df[c]))
            
    cov_matrix = returns_df.cov().values
    n = len(returns_df.columns)
    
    def risk_budget_objective(weights, cov):
        weights = np.array(weights)
        port_var = weights.T @ cov @ weights
        if port_var == 0: return 1e9
        marginal_risk = cov @ weights
        risk_contrib = weights * marginal_risk
        # 目标：让每个资产的风险贡献度完全相等（风控平权）
        target_risk = port_var / n
        return np.sum((risk_contrib - target_risk)**2) * 1e6
        
    init_weights = np.ones(n) / n
    bounds = [(0.0, 1.0) for _ in range(n)]
    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
    
    try:
        res = minimize(risk_budget_objective, init_weights, args=(cov_matrix,),
                       method='SLSQP', bounds=bounds, constraints=cons)
        final_weights_arr = res.x if res.success else init_weights
    except Exception as e:
        logger.warning(f"Risk Parity 优化失败({e})，降级为等权模式。")
        final_weights_arr = init_weights
        
    # 打包为可视化权重字典，并合并回 Top 10 列表
    weight_dict = {code: float(w) for code, w in zip(returns_df.columns, final_weights_arr)}
    top10_slice['Target_Weight'] = top10_slice['code'].map(weight_dict)
    
    # 格式化输出百分比
    top10_slice['Weight_%'] = top10_slice['Target_Weight'].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "0.00%")
    
    print("\n" + "="*70)
    print(f" 🚀 A 股明日最强看涨名单 & Risk Parity 仓位计算表 (基于 {last_date.date()} 行情) ")
    print("="*70)
    # 取出有用的列展示
    display_cols = ['code', 'close', 'pctChg', 'amount', 'rank_score', 'Weight_%']
    display_cols = [c for c in display_cols if c in top10_slice.columns]
    
    # 由于 pandas 的 to_markdown 依赖 tabulate，这里直接用内置 print 对齐打印，防止用户没装 tabulate
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(top10_slice[display_cols].to_string(index=False))
    print("="*70)
    print("⚠️ 指令已生成：请严格按照 `Weight_%` 的百分比分配并买入您的总仓位金额！")

if __name__ == "__main__":
    run_daily_trading()
