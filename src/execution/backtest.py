import pandas as pd
import numpy as np
from datetime import timedelta
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class Backtester:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {} # {code: shares}
        # T+1 logic: Positions bought today are locked.
        self.locked_positions = {} # {code: shares}
        self.history = []

    def execute_daily(self, date, alpha_scores, daily_data_dict):
        """
        Execute trades based on Alpha scores
        alpha_scores: dict {code: score}
        daily_data_dict: dict {code: {open, close, limit_up, limit_down, ...}}
        """
        # 1. Unlock yesterday's bought positions
        for code, shares in self.locked_positions.items():
            current = self.positions.get(code, 0)
            # Effectively they are already in self.positions, just marked as "locked" logically
            # In this simple engine, we just clear the locked dict at the start of day T
            # implying T-1 buys are now sellable.
            pass
        self.locked_positions = {}
        
        # 2. Strategy Logic: Top K
        # Select top 10 stocks
        sorted_alpha = sorted(alpha_scores.items(), key=lambda x: x[1], reverse=True)
        top_k = [x[0] for x in sorted_alpha[:50]] # Top 50
        
        # Target Weight (Equal weight)
        target_weight = 1.0 / len(top_k) if top_k else 0
        total_asset = self.get_total_asset(daily_data_dict)
        
        # 3. Generate Orders
        # Sell Logic
        current_codes = list(self.positions.keys())
        for code in current_codes:
            if code not in top_k:
                # Sell all
                self._sell(code, daily_data_dict.get(code), total_asset)
                
        # Buy Logic
        for code in top_k:
            self._buy(code, target_weight, daily_data_dict.get(code), total_asset)
            
        # 4. Record
        self.history.append({
            'date': date,
            'asset': self.get_total_asset(daily_data_dict),
            'cash': self.cash
        })
        
    def _sell(self, code, market_data, total_asset):
        if not market_data: return
        # Check Limit Up (cannot buy) / Limit Down (cannot sell)
        if market_data.get('is_limit_down'):
            return # Stuck
            
        shares = self.positions.get(code, 0)
        if shares > 0:
            price = market_data['close'] # Simulating Close execution
            amount = shares * price
            cost = amount * 0.0013 # Comm + Tax
            self.cash += (amount - cost)
            del self.positions[code]
            
    def _buy(self, code, target_weight, market_data, total_asset):
        if not market_data: return
        if market_data.get('is_limit_up'):
            return # Cannot buy
            
        target_amt = total_asset * target_weight
        price = market_data['close']
        
        # Already hold?
        if code in self.positions:
            return # Rebalance logic omitted for simplicity
            
        # Calc shares
        shares = int(target_amt / price / 100) * 100
        if shares == 0: return
        
        cost = shares * price
        fee = cost * 0.0003
        
        if self.cash >= (cost + fee):
            self.cash -= (cost + fee)
            self.positions[code] = shares
            self.locked_positions[code] = shares
            
    def get_total_asset(self, daily_data_dict):
        mkt_val = 0
        for code, shares in self.positions.items():
            price = 0
            if daily_data_dict and code in daily_data_dict:
                 price = daily_data_dict[code]['close']
            mkt_val += shares * price
        return self.cash + mkt_val

    def get_metrics(self):
        """
        计算回测指标 (优化版)
        
        新增:
        - Turnover: 换手率统计
        - Fitness Score: Sharpe / sqrt(Turnover) 
          (文档推荐: 惩罚高换手策略)
        """
        if not self.history: 
            return {}
            
        df = pd.DataFrame(self.history)
        
        # 1. 基础收益统计
        df['return'] = df['asset'].pct_change()
        mean_ret = df['return'].mean()
        std_ret = df['return'].std()
        
        if std_ret == 0:
            sharpe = 0
        else:
            sharpe = mean_ret / std_ret * np.sqrt(252)
        
        # 2. 换手率统计 (简化:用asset变化幅度近似)
        # 真实Turnover需要跟踪每日交易额,这里用资产波动率作为proxy
        df['asset_change'] = df['asset'].diff().abs()
        avg_turnover = (df['asset_change'] / df['asset']).mean()
        
        # 3. Fitness Score计算
        # Fitness = Sharpe / sqrt(Turnover)
        # 防止除零
        if avg_turnover > 0:
            fitness_score = sharpe / np.sqrt(avg_turnover)
        else:
            fitness_score = sharpe
        
        return {
            'sharpe': sharpe, 
            'final_asset': df['asset'].iloc[-1],
            'avg_turnover': avg_turnover,
            'fitness_score': fitness_score
        }

