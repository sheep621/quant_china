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

    def _calculate_risk_parity_weights(self, target_codes):
        """工业级协方差 Risk Parity (等风险贡献) 算法"""
        n = len(target_codes)
        if n == 0: return {}
        if n == 1: return {target_codes[0]: 1.0}
            
        returns_list = []
        valid_codes = []
        for code in target_codes:
            prices = self.price_history.get(code, [])
            if len(prices) >= 10:  # 至少需要10天数据来计算协方差
                prices_arr = np.array(prices, dtype=float)
                rets = np.diff(prices_arr) / (prices_arr[:-1] + 1e-8)
                returns_list.append(rets)
                valid_codes.append(code)
        
        if len(valid_codes) < n:
            # 数据不足时降级为等权重
            return {code: 1.0 / n for code in target_codes}
            
        # 构建协方差矩阵
        returns_matrix = np.vstack(returns_list)
        cov_matrix = np.cov(returns_matrix)
        
        # 凸优化目标：使各资产的边际风险贡献 (Risk Contribution) 相等
        def risk_budget_objective(weights, cov):
            weights = np.array(weights)
            port_var = weights.T @ cov @ weights
            marginal_risk = cov @ weights
            risk_contrib = weights * marginal_risk
            target_risk = port_var / len(weights)
            return np.sum(np.square(risk_contrib - target_risk))
            
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(len(valid_codes)))
        initial_guess = np.ones(len(valid_codes)) / len(valid_codes)
        
        try:
            from scipy.optimize import minimize
            res = minimize(risk_budget_objective, initial_guess, args=(cov_matrix,), 
                           method='SLSQP', bounds=bounds, constraints=constraints)
            weights = res.x if res.success else initial_guess
        except Exception as e:
            logger.warning(f"Risk Parity 优化失败，降级为等权: {e}")
            weights = initial_guess
            
        final_weights = {code: 0.0 for code in target_codes}
        for idx, code in enumerate(valid_codes):
            final_weights[code] = weights[idx]
            
        return final_weights



    def execute_daily(self, date, alpha_scores, daily_data_dict):
        current_value = self.cash
        
        # 1. 更新市值与历史价格
        for code in list(self.positions.keys()):
            if code in daily_data_dict:
                current_price = daily_data_dict[code].get('close', daily_data_dict[code].get('open', 0))
                current_value += self.positions[code] * current_price
                if code not in self.price_history: self.price_history[code] = []
                self.price_history[code].append(current_price)
                if len(self.price_history[code]) > 20: self.price_history[code].pop(0)

        # 2. 选出 Alpha 最高的 Top N 并计算协方差权重
        sorted_codes = sorted(alpha_scores, key=alpha_scores.get, reverse=True)
        target_codes = sorted_codes[:self.top_n]
        target_weights = self._calculate_risk_parity_weights(target_codes)

        # 3. 执行卖出 (释放资金)
        for code in list(self.positions.keys()):
            if code not in target_codes:
                if code not in daily_data_dict: continue
                day_data = daily_data_dict[code]
                open_price = day_data.get('open', 0)
                prev_close = day_data.get('pre_close', open_price) 
                
                _, can_sell = self.exchange.check_trade_limit(code, open_price, prev_close, day_data.get('high', 0), day_data.get('low', 0))
                self.total_orders += 1
                if not can_sell:
                    self.failed_orders += 1
                    continue

                exec_price = self.exchange.get_actual_sell_price(open_price)
                net_cash, _ = self.exchange.calculate_sell_cash(exec_price, self.positions[code])
                self.cash += net_cash
                del self.positions[code]

        # 4. 执行买入 (统筹分配可用资金池)
        buy_list = [c for c in target_codes if c not in self.positions]
        if buy_list:
            total_buy_weight = sum(target_weights[c] for c in buy_list)
            available_cash = self.cash  # 锁定当前可用总弹药
            
            for code in buy_list:
                if total_buy_weight <= 0: break
                if code not in daily_data_dict: continue
                    
                day_data = daily_data_dict[code]
                open_price = day_data.get('open', 0)
                prev_close = day_data.get('pre_close', open_price)
                
                can_buy, _ = self.exchange.check_trade_limit(code, open_price, prev_close, day_data.get('high', 0), day_data.get('low', 0))
                self.total_orders += 1
                if not can_buy:
                    self.failed_orders += 1
                    continue

                # 根据股票在该批买入池中的相对权重，切分现金蛋糕
                weight_in_pool = target_weights[code] / total_buy_weight
                allocated_cash = available_cash * weight_in_pool
                
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