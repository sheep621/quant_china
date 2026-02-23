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
        self.last_prices = {} # {code: last_close_price}

    def execute_daily(self, date, alpha_scores, daily_data_dict):
        """
        Execute trades based on Alpha scores
        alpha_scores: dict {code: score}
        daily_data_dict: dict {code: {open, close, limit_up, limit_down, ...}}
        """
        # 0. Update last known prices
        for code, data in daily_data_dict.items():
            if 'close' in data and not pd.isna(data['close']):
                self.last_prices[code] = data['close']
                
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
        # A股 T+1 交易：T日盘后决策，T+1日开盘执行（若T+1开盘跌停则报单被锁死无法成交）
        if market_data.get('next_is_limit_down', market_data.get('is_limit_down', False)):
            logger.info(f"{code} is LIMIT DOWN next day. Cannot sell.")
            return # Stuck
            
        shares = self.positions.get(code, 0)
        if shares > 0:
            # 必须且只能在 T+1 开盘价成交以杜绝未来函数
            if 'next_open' not in market_data or pd.isna(market_data['next_open']) or market_data['next_open'] <= 0:
                logger.debug(f"{code} is missing next_open. Cannot sell.")
                return
            price = market_data['next_open']
            # Slippage: Sell lower
            exec_price = price * (1 - 0.001)  # 0.1% slippage
            amount = shares * exec_price
            cost = amount * 0.0007 # Comm (0.02%) + Stamp Tax (0.05% - valid from Aug 2023)
            self.cash += (amount - cost)
            del self.positions[code]
            
    def _buy(self, code, target_weight, market_data, total_asset):
        if not market_data: return
        # A股 T+1 交易：如果 T+1 开盘价即涨停（一字板或者竞价秒板），则无法买入
        if market_data.get('next_is_limit_up', market_data.get('is_limit_up', False)):
            logger.info(f"{code} is LIMIT UP next day. Cannot buy.")
            return # Cannot buy
            
        target_amt = total_asset * target_weight
        # 必须在 T+1 的开盘成交
        if 'next_open' not in market_data or pd.isna(market_data['next_open']) or market_data['next_open'] <= 0:
            logger.debug(f"{code} is missing next_open. Cannot buy.")
            return
        price = market_data['next_open']
        
        # Already hold?
        if code in self.positions:
            return # Rebalance logic omitted for simplicity
            
        # Slippage: Buy higher
        exec_price = price * (1 + 0.001) # 0.1% slippage
        
        # Calc shares (A股需为100的整数倍)
        shares = int(target_amt / exec_price / 100) * 100
        if shares == 0: return
        
        cost = shares * exec_price
        fee = cost * 0.0002 # Comm (0.02%) No Stamp Tax on Buy
        
        # 如果资金不足，重新计算最大可买入股数，而不是直接放弃交易
        if self.cash < cost + fee:
            max_shares = int(self.cash / (exec_price * 1.0002) / 100) * 100
            if max_shares == 0: return
            shares = max_shares
            cost = shares * exec_price
            fee = cost * 0.0002
            
        self.cash -= (cost + fee)
        self.positions[code] = shares
        self.locked_positions[code] = shares
            
    def get_total_asset(self, daily_data_dict):
        mkt_val = 0
        for code, shares in self.positions.items():
            price = self.last_prices.get(code, 0.0)
            if daily_data_dict and code in daily_data_dict:
                 current_close = daily_data_dict[code].get('close', 0.0)
                 if current_close > 0:
                     price = current_close
            mkt_val += shares * price
        return self.cash + mkt_val

    def get_metrics(self):
        """
        Calculates professional metrics:
        - Total Return
        - Annualized Return (CAGR)
        - Max Drawdown
        - Sharpe Ratio
        - Avg Turnover
        """
        if not self.history: 
            return {}
            
        df = pd.DataFrame(self.history)
        
        # 1. Basic Returns
        df['return'] = df['asset'].pct_change().fillna(0)
        total_ret = (df['asset'].iloc[-1] / self.initial_capital) - 1
        
        # 2. Annualized Return
        days = len(df)
        if days > 0:
            cagr = (df['asset'].iloc[-1] / self.initial_capital) ** (252/days) - 1
        else:
            cagr = 0
            
        # 3. Max Drawdown
        df['cummax'] = df['asset'].cummax()
        df['drawdown'] = (df['asset'] - df['cummax']) / df['cummax']
        max_dd = df['drawdown'].min()
        
        # 4. Sharpe
        mean_ret = df['return'].mean()
        std_ret = df['return'].std()
        if std_ret < 1e-6:
            sharpe = 0
        else:
            sharpe = mean_ret / std_ret * np.sqrt(252)
        
        # 5. Turnover Proxy
        df['asset_change'] = df['asset'].diff().abs()
        avg_turnover = (df['asset_change'] / df['asset']).mean()
        
        return {
            'total_return': f"{total_ret*100:.2f}%",
            'cagr': f"{cagr*100:.2f}%",
            'max_drawdown': f"{max_dd*100:.2f}%",
            'sharpe': f"{sharpe:.2f}",
            'final_asset': f"{df['asset'].iloc[-1]:.2f}",
        }

