import pandas as pd
import numpy as np
import json
import os
from src.infrastructure.logger import get_system_logger
from src.model_layer.lgbm_trainer import LGBMTrainer

logger = get_system_logger()

class DailyInference:
    def __init__(self, model_path='output/lgbm_model.txt', top_n=10):
        self.model_path = model_path
        self.top_n = top_n
        self.trainer = LGBMTrainer()
        if os.path.exists(self.model_path):
            self.trainer.load_model(self.model_path)
        else:
            logger.warning("Model file not found. Inference will fail if not trained.")

    def run_inference(self, daily_df, features):
        """
        为最新交易日执行推理，并生成结合了 Risk Parity 权重的实盘调仓名单。
        注意：daily_df 应包含最新截面数据以及用于计算波动的过去 20 天数据。
        """
        if self.trainer.model is None:
            raise ValueError("Model not loaded.")
            
        latest_date = daily_df['date'].max()
        today_df = daily_df[daily_df['date'] == latest_date].copy()
        
        if today_df.empty:
            logger.error(f"No data available for {latest_date}")
            return
            
        # 1. LGBM 模型预测截面得分
        preds = self.trainer.predict(today_df, features)
        today_df['score'] = preds
        
        # 2. 截取 Top N
        top_stocks = today_df.sort_values('score', ascending=False).head(self.top_n)
        
        # 3. 计算 Risk Parity (历史波动率倒数) 目标权重
        target_portfolio = []
        
        for _, row in top_stocks.iterrows():
            code = row['code']
            # 切片该股票过去 20 天的数据计算真实波动率
            history_slice = daily_df[(daily_df['code'] == code) & (daily_df['date'] <= latest_date)].tail(20)
            
            if len(history_slice) < 5:
                vol = 1.0  # 惩罚数据不足的次新股
            else:
                rets = history_slice['close'].pct_change().dropna()
                vol = rets.std()
                
            inv_vol = 1.0 / (vol + 1e-5)
            
            target_portfolio.append({
                'code': code,
                'score': float(row['score']),
                'inv_vol': float(inv_vol),
                'close': float(row['close']),
                'name': row.get('name', 'N/A')
            })
            
        # 归一化处理得到最终仓位百分比
        total_inv_vol = sum(item['inv_vol'] for item in target_portfolio)
        for item in target_portfolio:
            item['weight'] = item['inv_vol'] / total_inv_vol
            
        # 4. 导出给实盘执行模块的 JSON 指令
        output_data = {
            'date': str(latest_date),
            'portfolio': target_portfolio
        }
        
        os.makedirs('output', exist_ok=True)
        out_file = f"output/target_portfolio_{str(latest_date)[:10]}.json"
        with open(out_file, 'w') as f:
            json.dump(output_data, f, indent=4)
            
        logger.info(f"Inference completed for {latest_date}. Saved to {out_file}")
        
        logger.info("=== 🚀 Target Portfolio (Risk Parity Weighted) ===")
        for item in target_portfolio:
            logger.info(f"Code: {item['code']:<10} | Score: {item['score']:.4f} | Target Weight: {item['weight']:.2%}")
            
        return output_data