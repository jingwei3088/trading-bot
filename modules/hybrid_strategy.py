"""
趋势跟踪 + 网格混合策略

核心逻辑：
- 趋势向上时：持有核心仓位 + 网格加仓
- 趋势向下时：减仓 + 停止网格买入
- 震荡时：正常网格交易
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.append('..')
from config import GRID_CONFIG


class MarketState(Enum):
    BULL = "BULL"       # 牛市
    BEAR = "BEAR"       # 熊市
    RANGE = "RANGE"     # 震荡


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    """持仓记录"""
    entry_price: float
    amount: float
    entry_time: str = ""


@dataclass 
class TradeSignal:
    """交易信号"""
    side: OrderSide
    price: float
    amount: float
    reason: str = ""
    timestamp: str = ""


class HybridStrategy:
    """趋势+网格混合策略"""
    
    def __init__(self):
        self.config = GRID_CONFIG
        self.positions: List[Position] = []  # 所有持仓
        self.grid_center = 0.0
        self.last_buy_price = 0.0
        self.last_sell_price = 0.0
        self.total_position = 0.0
        self.total_cost = 0.0
        
    def detect_market_state(self, price: float, ema_fast: float, ema_slow: float, ema_trend: float) -> MarketState:
        """
        判断市场状态
        """
        # 价格在长期EMA上方且短期EMA > 长期EMA = 牛市
        if price > ema_trend and ema_fast > ema_slow:
            return MarketState.BULL
        # 价格在长期EMA下方且短期EMA < 长期EMA = 熊市  
        elif price < ema_trend and ema_fast < ema_slow:
            return MarketState.BEAR
        else:
            return MarketState.RANGE
    
    def process(
        self,
        price: float,
        ema_fast: float,
        ema_slow: float,
        ema_trend: float,
        atr_pct: float,
        timestamp: str = ""
    ) -> List[TradeSignal]:
        """
        处理价格，生成交易信号
        """
        signals = []
        
        # 判断市场状态
        state = self.detect_market_state(price, ema_fast, ema_slow, ema_trend)
        
        # 动态调整网格间距
        grid_size = np.clip(
            atr_pct * 2.5,
            self.config['min_grid_size'],
            self.config['max_grid_size']
        )
        
        order_amount = self.config['order_amount']
        
        # === 买入逻辑 ===
        should_buy = False
        buy_reason = ""
        
        if state == MarketState.BULL:
            # 牛市：积极买入
            if self.last_buy_price == 0:
                should_buy = True
                buy_reason = "牛市初始建仓"
            elif price <= self.last_buy_price * (1 - grid_size):
                should_buy = True
                buy_reason = f"牛市回调买入 (跌{grid_size*100:.1f}%)"
                
        elif state == MarketState.RANGE:
            # 震荡：正常网格
            if self.last_buy_price == 0:
                should_buy = True
                buy_reason = "震荡市初始建仓"
            elif price <= self.last_buy_price * (1 - grid_size):
                should_buy = True
                buy_reason = f"网格买入 (跌{grid_size*100:.1f}%)"
                
        elif state == MarketState.BEAR:
            # 熊市：非常谨慎，只在大跌后买入
            if self.last_buy_price > 0 and price <= self.last_buy_price * (1 - grid_size * 2):
                should_buy = True
                buy_reason = f"熊市抄底 (跌{grid_size*200:.1f}%)"
        
        if should_buy:
            signals.append(TradeSignal(
                side=OrderSide.BUY,
                price=price,
                amount=order_amount,
                reason=buy_reason,
                timestamp=timestamp
            ))
        
        # === 卖出逻辑 ===
        # 检查每个持仓是否应该卖出
        positions_to_sell = []
        
        for i, pos in enumerate(self.positions):
            profit_pct = (price - pos.entry_price) / pos.entry_price
            
            should_sell = False
            sell_reason = ""
            
            if state == MarketState.BULL:
                # 牛市：宽松止盈，让利润奔跑
                if profit_pct >= grid_size * 2:
                    should_sell = True
                    sell_reason = f"牛市止盈 (+{profit_pct*100:.1f}%)"
                    
            elif state == MarketState.RANGE:
                # 震荡：正常网格止盈
                if profit_pct >= grid_size:
                    should_sell = True
                    sell_reason = f"网格止盈 (+{profit_pct*100:.1f}%)"
                    
            elif state == MarketState.BEAR:
                # 熊市：快速止盈，落袋为安
                if profit_pct >= grid_size * 0.5:
                    should_sell = True
                    sell_reason = f"熊市快速止盈 (+{profit_pct*100:.1f}%)"
                # 熊市止损
                elif profit_pct <= -grid_size * 3:
                    should_sell = True
                    sell_reason = f"熊市止损 ({profit_pct*100:.1f}%)"
            
            if should_sell:
                positions_to_sell.append((i, pos, sell_reason))
        
        # 从后往前删除，避免索引问题
        for i, pos, reason in reversed(positions_to_sell):
            signals.append(TradeSignal(
                side=OrderSide.SELL,
                price=price,
                amount=pos.amount,
                reason=reason,
                timestamp=timestamp
            ))
        
        return signals
    
    def execute_buy(self, price: float, amount: float, timestamp: str = ""):
        """执行买入"""
        self.positions.append(Position(
            entry_price=price,
            amount=amount,
            entry_time=timestamp
        ))
        self.last_buy_price = price
        self.total_position += amount
        self.total_cost += price * amount
    
    def execute_sell(self, price: float, amount: float) -> float:
        """
        执行卖出，返回盈亏
        采用FIFO原则（先进先出）
        """
        remaining = amount
        total_pnl = 0.0
        
        while remaining > 0 and self.positions:
            pos = self.positions[0]
            
            if pos.amount <= remaining:
                # 整个仓位卖出
                pnl = (price - pos.entry_price) * pos.amount
                total_pnl += pnl
                remaining -= pos.amount
                self.total_position -= pos.amount
                self.total_cost -= pos.entry_price * pos.amount
                self.positions.pop(0)
            else:
                # 部分卖出
                pnl = (price - pos.entry_price) * remaining
                total_pnl += pnl
                pos.amount -= remaining
                self.total_position -= remaining
                self.total_cost -= pos.entry_price * remaining
                remaining = 0
        
        if self.positions:
            self.last_sell_price = price
        else:
            self.last_buy_price = 0
            self.last_sell_price = 0
            
        return total_pnl
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏"""
        return sum((current_price - pos.entry_price) * pos.amount for pos in self.positions)
    
    def get_position_value(self, current_price: float) -> float:
        """计算持仓市值"""
        return self.total_position * current_price
