import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class Backtester:
    def __init__(self, initial_capital=1000000.0, top_n=10):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {code: shares}
        self.history = []
        self.top_n = top_n
        
        # 内部状态：维护过去 20 天的收盘价，用于计算 Risk Parity 的真实历史波动率
        self.price_history = {} 

    def _calculate_inverse_volatility_weights(self, target_codes):
        """任务 5.3：计算历史波动率倒数加权 (Risk Parity 简易版)"""
        inv_vols = {}
        for code in target_codes:
            prices = self.price_history.get(code, [])
            if len(prices) < 5:
                inv_vols[code] = 1.0  # 数据不足，给予默认低权重基数
            else:
                rets = np.diff(prices) / prices[:-1]
                vol = np.std(rets)
                # 波动率越大，倒数越小，权重越低；加上 1e-5 防止除零
                inv_vols[code] = 1.0 / (vol + 1e-5)
        
        total_inv_vol = sum(inv_vols.values())
        if total_inv_vol == 0:
            return {code: 1.0 / len(target_codes) for code in target_codes}
        
        return {code: v / total_inv_vol for code, v in inv_vols.items()}

    def execute_daily(self, date, alpha_scores, daily_data):
        """执行每日撮合"""
        # 1. 滚动更新所有股票的价格历史，供波动率计算使用
        for code, data in daily_data.items():
            if code not in self.price_history:
                self.price_history[code] = []
            self.price_history[code].append(data.get('close', data.get('open', 0)))
            if len(self.price_history[code]) > 20:
                self.price_history[code].pop(0)

        if not alpha_scores:
            self._record_history(date)
            return

        # 2. 选出 Top N 的标的
        sorted_codes = sorted(alpha_scores.keys(), key=lambda x: alpha_scores[x], reverse=True)
        target_codes = sorted_codes[:self.top_n]

        # 3. 计算 Risk Parity 目标权重
        weights = self._calculate_inverse_volatility_weights(target_codes)

        # 计算当前账户总净值
        current_value = self.cash
        for code, shares in self.positions.items():
            current_value += shares * daily_data.get(code, {}).get('open', 0)

        # 4. 计算目标持仓股数 (向下取整到 100 股)
        target_positions = {}
        for code in target_codes:
            if code not in daily_data: continue
            target_amt = current_value * weights[code]
            open_price = daily_data[code].get('open', 0)
            if open_price > 0:
                target_positions[code] = int(target_amt / open_price / 100) * 100

        # ==========================================
        # 5. 执行卖出 (先卖后买，释放资金)
        # ==========================================
        for code in list(self.positions.keys()):
            current_shares = self.positions[code]
            target_shares = target_positions.get(code, 0)
            
            if current_shares > target_shares:
                sell_shares = current_shares - target_shares
                data = daily_data.get(code)
                if not data: continue
                
                open_price = data.get('open', 0)
                low_limit = data.get('low_limit', 0)
                daily_vol = data.get('volume', 1e8) 
                
                # 任务 5.2: T+1 一字跌停拦截 (只看开盘价)
                if open_price <= low_limit + 0.01:
                    logger.debug(f"[{date}] {code} 开盘跌停，毫无流动性，拒绝卖出")
                    continue
                    
                # 任务 5.1: 流动性容量限制 (单日卖出不得超过该股总成交量的 10%)
                max_sell = int(daily_vol * 0.1 / 100) * 100
                actual_sell = min(sell_shares, max_sell)
                
                if actual_sell > 0:
                    # 任务 5.1: 动态冲击成本 (Almgren-Chriss 简易版)
                    # 基础滑点千分之一 + 与成交占比平方根成正比的冲击成本
                    impact = 0.001 + 0.1 * np.sqrt(actual_sell / (daily_vol + 1e-8))
                    exec_price = open_price * (1 - impact) # 卖得越多，成交均价越低
                    
                    self.cash += actual_sell * exec_price
                    self.positions[code] -= actual_sell
                    if self.positions[code] == 0:
                        del self.positions[code]

        # ==========================================
        # 6. 执行买入
        # ==========================================
        for code, target_shares in target_positions.items():
            current_shares = self.positions.get(code, 0)
            if target_shares > current_shares:
                buy_shares = target_shares - current_shares
                data = daily_data.get(code)
                if not data: continue
                
                open_price = data.get('open', 0)
                high_limit = data.get('high_limit', 9999)
                daily_vol = data.get('volume', 1e8)
                
                # 任务 5.2: T+1 一字涨停拦截 (只看开盘价)
                if open_price >= high_limit - 0.01:
                    logger.debug(f"[{date}] {code} 开盘一字板，排队无望，拒绝买入")
                    continue
                    
                # 任务 5.1: 流动性容量限制
                max_buy = int(daily_vol * 0.1 / 100) * 100
                actual_buy = min(buy_shares, max_buy)
                
                # 资金限制重检
                cost = actual_buy * open_price
                if cost > self.cash:
                    actual_buy = int(self.cash / open_price / 100) * 100
                    
                if actual_buy > 0:
                    # 任务 5.1: 动态冲击成本
                    impact = 0.001 + 0.1 * np.sqrt(actual_buy / (daily_vol + 1e-8))
                    exec_price = open_price * (1 + impact) # 买得越多，成交均价被拉得越高
                    
                    if self.cash >= actual_buy * exec_price:
                        self.cash -= actual_buy * exec_price
                        self.positions[code] = self.positions.get(code, 0) + actual_buy

        self._record_history(date, current_value)

    def _record_history(self, date, value=None):
        if value is None:
            value = self.cash
        self.history.append({'date': date, 'value': value})

    def get_metrics(self):
        if not self.history: return {}
        df = pd.DataFrame(self.history)
        df['return'] = df['value'].pct_change().fillna(0)
        cum_ret = df['value'].iloc[-1] / self.initial_capital - 1
        annual_ret = (1 + cum_ret) ** (252 / len(df)) - 1 if len(df) > 0 else 0
        std = df['return'].std() * np.sqrt(252)
        sharpe = annual_ret / std if std > 0 else 0
        
        # 附加最大回撤统计
        roll_max = df['value'].cummax()
        drawdown = df['value'] / roll_max - 1.0
        max_dd = drawdown.min()
        
        return {
            'cum_return': f"{cum_ret:.2%}", 
            'annual_return': f"{annual_ret:.2%}", 
            'sharpe': f"{sharpe:.2f}",
            'max_drawdown': f"{max_dd:.2%}"
        }