import math
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class AshareExchange:
    def __init__(self, commission_rate=0.0003, stamp_duty=0.001, min_commission=5.0, fixed_slippage=0.002):
        """
        A股交易环境参数
        commission_rate: 券商佣金率 (默认万三)
        stamp_duty: 印花税 (仅卖出收取，默认千一)
        min_commission: 最低佣金要求 (5元)
        fixed_slippage: 固定滑点成本 (日频回测中，由于缺乏高频订单簿，使用固定千分之二替代未来函数计算)
        """
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.min_commission = min_commission
        self.fixed_slippage = fixed_slippage

    def check_trade_limit(self, code, open_price, prev_close, high_price, low_price):
        """
        涨跌停与停牌过滤器
        返回: (can_buy, can_sell)
        """
        # 如果缺少前收盘价或当前开盘价，视为停牌或数据缺失
        if not open_price or not prev_close or math.isnan(open_price):
            return False, False
            
        limit_up_price = round(prev_close * 1.10, 2)
        limit_down_price = round(prev_close * 0.90, 2)

        can_buy = True
        can_sell = True

        # 开盘即涨停（或一字板），普通测试资金无法买入
        if open_price >= limit_up_price:
            can_buy = False
            
        # 开盘即跌停，无法卖出止损
        if open_price <= limit_down_price:
            can_sell = False

        return can_buy, can_sell

    def get_actual_buy_price(self, open_price):
        """加入开盘滑点后的真实买入单价"""
        return open_price * (1 + self.fixed_slippage)

    def get_actual_sell_price(self, open_price):
        """加入开盘滑点后的真实卖出单价"""
        return open_price * (1 - self.fixed_slippage)

    def calculate_buy_cost(self, price, shares):
        """核算买入总成本（含税费）"""
        trade_value = price * shares
        commission = max(trade_value * self.commission_rate, self.min_commission)
        total_cost = trade_value + commission
        return total_cost, commission

    def calculate_sell_cash(self, price, shares):
        """核算卖出后的净流入资金"""
        trade_value = price * shares
        commission = max(trade_value * self.commission_rate, self.min_commission)
        stamp = trade_value * self.stamp_duty
        net_cash = trade_value - commission - stamp
        return net_cash, commission + stamp

    def get_max_buyable_shares(self, cash, price):
        """
        【漏洞修复】：精确计算资金最大可买手数
        取代之前先除单价再判断余额导致漏单的逻辑
        """
        # 粗略计算最大股数 (向下取整到百股)
        rough_shares = math.floor(cash / price / 100) * 100
        
        # 递减尝试，直到包含最低5元佣金的总成本小于可用资金
        while rough_shares > 0:
            total_cost, _ = self.calculate_buy_cost(price, rough_shares)
            if total_cost <= cash:
                return rough_shares
            rough_shares -= 100
            
        return 0