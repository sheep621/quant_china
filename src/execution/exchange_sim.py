import math
from src.infrastructure.logger import get_system_logger

logger = get_system_logger()

class AshareExchange:
    def __init__(self, commission_rate=0.0003, stamp_duty=0.001, min_commission=5.0, fixed_slippage=0.002):
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.min_commission = min_commission
        self.fixed_slippage = fixed_slippage

    def check_trade_limit(self, code, open_price, prev_close, high_price, low_price):
        if not open_price or math.isnan(open_price):
            return False, False
            
        can_buy = True
        can_sell = True

        # 1. 终极防线：无论涨跌停，最高价等于最低价说明全天无波动，绝对无法成交
        if high_price > 0 and high_price == low_price:
            can_buy = False
            can_sell = False

        # 2. 软性涨跌停限制 (放宽到 20.5% 以兼容科创板/创业板，防止误杀)
        if prev_close and prev_close > 0:
            limit_up_price = prev_close * 1.205 
            limit_down_price = prev_close * 0.795
            if open_price >= limit_up_price:
                can_buy = False
            if open_price <= limit_down_price:
                can_sell = False

        return can_buy, can_sell

    def get_actual_buy_price(self, open_price):
        return open_price * (1 + self.fixed_slippage)

    def get_actual_sell_price(self, open_price):
        return open_price * (1 - self.fixed_slippage)

    def calculate_buy_cost(self, price, shares):
        trade_value = price * shares
        commission = max(trade_value * self.commission_rate, self.min_commission)
        return trade_value + commission, commission

    def calculate_sell_cash(self, price, shares):
        trade_value = price * shares
        commission = max(trade_value * self.commission_rate, self.min_commission)
        stamp = trade_value * self.stamp_duty
        return trade_value - commission - stamp, commission + stamp

    def get_max_buyable_shares(self, cash, price):
        # 增加 0.01% 的价格缓冲，防止由于浮点数精度导致的临界资金买入失败
        safe_price = price * 1.0001
        rough_shares = math.floor(cash / safe_price / 100) * 100
        
        while rough_shares > 0:
            total_cost, _ = self.calculate_buy_cost(price, rough_shares)
            if total_cost <= cash:
                return rough_shares
            rough_shares -= 100
            
        return 0