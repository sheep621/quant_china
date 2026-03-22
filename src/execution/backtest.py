import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger
from src.execution.exchange_sim import AshareExchange

logger = get_system_logger()

class Backtester:
    def __init__(self, initial_capital=1000000.0, top_n=10):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {code: shares}
        self.history = []
        self.top_n = top_n
        self.price_history = {} 
        
        # 引入重构后的交易所模拟器
        self.exchange = AshareExchange()
        
        # 执行监控指标
        self.total_orders = 0
        self.failed_orders = 0

    def _calculate_inverse_volatility_weights(self, target_codes):
        """风险平价雏形：计算历史波动率倒数加权"""
        inv_vols = {}
        for code in target_codes:
            prices = self.price_history.get(code, [])
            if len(prices) < 5:
                inv_vols[code] = 1.0  
            else:
                # 转换 array 并增加 1e-8 防止除以 0（如停牌假数据）
                prices_arr = np.array(prices, dtype=float)
                rets = np.diff(prices_arr) / (prices_arr[:-1] + 1e-8)
                vol = np.nan_to_num(np.std(rets), nan=0.0, posinf=0.0, neginf=0.0)
                inv_vols[code] = 1.0 / (vol + 1e-5)
                
        total_inv_vol = sum(inv_vols.values())
        if total_inv_vol == 0 or np.isnan(total_inv_vol):
            return {code: 1.0 / max(len(target_codes), 1) for code in target_codes}
            
        return {code: iv / total_inv_vol for code, iv in inv_vols.items()}

    def execute_daily(self, date, alpha_scores, daily_data_dict):
        """每日撮合逻辑：T+1 规则下的开盘执行"""
        current_value = self.cash
        
        # 1. 提取当前持仓的市值，并更新历史价格
        for code in list(self.positions.keys()):
            if code in daily_data_dict:
                current_price = daily_data_dict[code].get('close', daily_data_dict[code].get('open', 0))
                current_value += self.positions[code] * current_price
                
                if code not in self.price_history:
                    self.price_history[code] = []
                self.price_history[code].append(current_price)
                if len(self.price_history[code]) > 20:
                    self.price_history[code].pop(0)

        # 2. 选出 Alpha 最高的 Top N
        sorted_codes = sorted(alpha_scores, key=alpha_scores.get, reverse=True)
        target_codes = sorted_codes[:self.top_n]
        
        target_weights = self._calculate_inverse_volatility_weights(target_codes)
        target_values = {code: current_value * weight for code, weight in target_weights.items()}

        # 3. 执行卖出 (需先平仓释放资金)
        for code in list(self.positions.keys()):
            if code not in target_values:
                if code not in daily_data_dict:
                    continue
                
                day_data = daily_data_dict[code]
                open_price = day_data['open']
                # 假设 daily_data_dict 里带有昨收价 'pre_close'，如果没有可用 'open' 替代做粗略模拟
                prev_close = day_data.get('pre_close', open_price) 
                
                _, can_sell = self.exchange.check_trade_limit(code, open_price, prev_close, day_data['high'], day_data['low'])
                
                self.total_orders += 1
                if not can_sell:
                    self.failed_orders += 1
                    logger.debug(f"[{date}] {code} 触及跌停或停牌，卖出指令被拒绝")
                    continue

                sell_shares = self.positions[code]
                exec_price = self.exchange.get_actual_sell_price(open_price)
                net_cash, _ = self.exchange.calculate_sell_cash(exec_price, sell_shares)
                
                self.cash += net_cash
                del self.positions[code]

        # 4. 执行买入
        for code in target_codes:
            if code not in self.positions:
                if code not in daily_data_dict:
                    continue
                    
                day_data = daily_data_dict[code]
                open_price = day_data['open']
                prev_close = day_data.get('pre_close', open_price)
                
                can_buy, _ = self.exchange.check_trade_limit(code, open_price, prev_close, day_data['high'], day_data['low'])
                
                self.total_orders += 1
                if not can_buy:
                    self.failed_orders += 1
                    logger.debug(f"[{date}] {code} 触及涨停或停牌，买入指令被拒绝")
                    continue

                target_value = target_values[code]
                allocated_cash = min(self.cash, target_value)
                
                # 引入交易所引擎处理真实成交价和精确份额计算
                exec_price = self.exchange.get_actual_buy_price(open_price)
                actual_buy = self.exchange.get_max_buyable_shares(allocated_cash, exec_price)

                if actual_buy > 0:
                    total_cost, _ = self.exchange.calculate_buy_cost(exec_price, actual_buy)
                    self.cash -= total_cost
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
        
        # 新增执行层质量评估
        ffr = 1.0 - (self.failed_orders / max(self.total_orders, 1))
        
        # 🎯 核心升级：Benchmark 接入与超额收益计算
        try:
            from src.data_engine.loader import DataLoader
            loader = DataLoader()
            loader.login()
            
            # 从回测记录中提取开始和结束日期
            start_date = df['date'].min()
            end_date = df['date'].max()
            
            # 使用针对指数优化的专用接口
            bm_df = loader.fetch_benchmark_data(
                code="sh.000300", 
                start_date=str(start_date)[:10], 
                end_date=str(end_date)[:10]
            )
            loader.logout()
            
            if bm_df is not None and not bm_df.empty:
                # 统一为字符串格式对齐
                df['date_str'] = df['date'].dt.strftime('%Y-%m-%d') if pd.api.types.is_datetime64_any_dtype(df['date']) else df['date'].astype(str)
                bm_df['date_str'] = bm_df['date'].astype(str)
                
                # 合并基准涨跌幅
                merged = pd.merge(df, bm_df[['date_str', 'pctChg']], on='date_str', how='left')
                merged['bm_return'] = (merged['pctChg'] / 100).fillna(0)
                
                # 基准累计收益与超额收益
                bm_cum_ret = (1 + merged['bm_return']).prod() - 1
                excess_cum_ret = cum_ret - bm_cum_ret
                
                # 每日超额收益特征（用于核算信息比率）
                merged['excess_daily'] = merged['return'] - merged['bm_return']
                excess_std = merged['excess_daily'].std() * np.sqrt(252)
                excess_annual_ret = (1 + excess_cum_ret) ** (252 / len(df)) - 1 if len(df) > 0 else 0
                ir = excess_annual_ret / excess_std if excess_std > 0 else 0
                
                return {
                    "Absolute Cum. Return": round(cum_ret, 4),
                    "Benchmark Cum. Return": round(bm_cum_ret, 4),
                    "Excess Annual Return": round(excess_annual_ret, 4),
                    "Sharpe Ratio": round(sharpe, 4),
                    "Information Ratio (IR)": round(ir, 4),
                    "Full Fill Rate (FFR)": round(ffr, 4)
                }
        except Exception as e:
            logger.warning(f"Failed to calculate benchmark metrics: {e}")
            
        # Fallback 退化版本
        return {
            "Cumulative Return": round(cum_ret, 4),
            "Annualized Return": round(annual_ret, 4),
            "Sharpe Ratio": round(sharpe, 4),
            "Full Fill Rate (FFR)": round(ffr, 4)
        }