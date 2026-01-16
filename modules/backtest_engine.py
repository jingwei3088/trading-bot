"""
回测引擎 - 混合策略版本
"""
import pandas as pd
import numpy as np
from typing import List
from dataclasses import dataclass, field
import sys
sys.path.append('..')

from config import BACKTEST_CONFIG, RISK_CONFIG
from modules.hybrid_strategy import HybridStrategy, OrderSide


@dataclass
class Trade:
    timestamp: str
    side: str
    price: float
    amount: float
    pnl: float = 0.0
    balance: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestEngine:
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.initial_capital = BACKTEST_CONFIG['initial_capital']
        self.commission_rate = BACKTEST_CONFIG['commission_rate']
        
        self.cash = self.initial_capital
        self.strategy = HybridStrategy()
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        
    def run(self, verbose: bool = True) -> BacktestResult:
        if verbose:
            print(f"\n{'='*60}")
            print(f"开始回测")
            print(f"{'='*60}")
            print(f"初始资金: ${self.initial_capital:,.2f}")
            print(f"数据: {self.data['Date'].iloc[0]} ~ {self.data['Date'].iloc[-1]}")
        
        for _, row in self.data.iterrows():
            self._process_bar(row)
        
        # 结束时平仓
        self._close_all(self.data['Close'].iloc[-1], str(self.data['Date'].iloc[-1]))
        
        result = self._calculate_result()
        
        if verbose:
            self._print_result(result)
        
        return result
    
    def _process_bar(self, row):
        price = row['Close']
        timestamp = str(row['Date'])
        
        # 计算权益
        equity = self.cash + self.strategy.get_position_value(price)
        self.equity_curve.append(equity)
        
        # 风控检查：仓位限制
        position_ratio = self.strategy.get_position_value(price) / equity if equity > 0 else 0
        max_ratio = RISK_CONFIG['max_position_ratio']
        
        # 获取信号
        signals = self.strategy.process(
            price=price,
            ema_fast=row['EMA_fast'],
            ema_slow=row['EMA_slow'],
            ema_trend=row['EMA_trend'],
            atr_pct=row['ATR_pct'],
            timestamp=timestamp
        )
        
        for signal in signals:
            if signal.side == OrderSide.BUY:
                # 检查仓位限制
                if position_ratio >= max_ratio:
                    continue
                    
                cost = signal.price * signal.amount * (1 + self.commission_rate)
                if self.cash >= cost:
                    self.cash -= cost
                    self.strategy.execute_buy(signal.price, signal.amount, timestamp)
                    
                    self.trades.append(Trade(
                        timestamp=timestamp,
                        side="BUY",
                        price=signal.price,
                        amount=signal.amount,
                        pnl=0,
                        balance=self.cash,
                        reason=signal.reason
                    ))
                    
            elif signal.side == OrderSide.SELL:
                pnl = self.strategy.execute_sell(signal.price, signal.amount)
                commission = signal.price * signal.amount * self.commission_rate
                self.cash += signal.price * signal.amount - commission
                pnl -= commission
                
                self.trades.append(Trade(
                    timestamp=timestamp,
                    side="SELL",
                    price=signal.price,
                    amount=signal.amount,
                    pnl=pnl,
                    balance=self.cash,
                    reason=signal.reason
                ))
    
    def _close_all(self, price: float, timestamp: str):
        """平掉所有仓位"""
        for pos in self.strategy.positions[:]:
            pnl = (price - pos.entry_price) * pos.amount
            commission = price * pos.amount * self.commission_rate
            pnl -= commission
            self.cash += price * pos.amount - commission
            
            self.trades.append(Trade(
                timestamp=timestamp,
                side="SELL(CLOSE)",
                price=price,
                amount=pos.amount,
                pnl=pnl,
                balance=self.cash,
                reason="回测结束平仓"
            ))
        
        self.strategy.positions.clear()
        self.strategy.total_position = 0
    
    def _calculate_result(self) -> BacktestResult:
        result = BacktestResult()
        result.trades = self.trades
        result.equity_curve = self.equity_curve
        
        sell_trades = [t for t in self.trades if 'SELL' in t.side]
        result.total_trades = len(sell_trades)
        result.winning_trades = sum(1 for t in sell_trades if t.pnl > 0)
        result.losing_trades = sum(1 for t in sell_trades if t.pnl <= 0)
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        
        result.total_pnl = sum(t.pnl for t in sell_trades)
        result.total_pnl_pct = result.total_pnl / self.initial_capital
        
        # 最大回撤
        if self.equity_curve:
            peak = self.equity_curve[0]
            max_dd = 0
            for eq in self.equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            result.max_drawdown_pct = max_dd
            result.max_drawdown = peak * max_dd
        
        # Sharpe
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            if returns.std() > 0:
                result.sharpe_ratio = returns.mean() / returns.std() * np.sqrt(24 * 365)
        
        return result
    
    def _print_result(self, result: BacktestResult):
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        
        print(f"\n{'='*60}")
        print("回测结果")
        print(f"{'='*60}")
        print(f"\n【收益】")
        print(f"  初始资金:   ${self.initial_capital:>12,.2f}")
        print(f"  最终权益:   ${final_equity:>12,.2f}")
        print(f"  总收益:     ${result.total_pnl:>12,.2f} ({result.total_pnl_pct:+.2%})")
        
        print(f"\n【交易】")
        print(f"  总交易:     {result.total_trades:>12}")
        print(f"  盈利:       {result.winning_trades:>12}")
        print(f"  亏损:       {result.losing_trades:>12}")
        print(f"  胜率:       {result.win_rate:>12.2%}")
        
        print(f"\n【风险】")
        print(f"  最大回撤:   {result.max_drawdown_pct:>12.2%}")
        print(f"  Sharpe:     {result.sharpe_ratio:>12.2f}")
        print(f"{'='*60}")
    
    def export_trades(self, filepath: str):
        df = pd.DataFrame([{
            'timestamp': t.timestamp,
            'side': t.side,
            'price': t.price,
            'amount': t.amount,
            'pnl': t.pnl,
            'balance': t.balance,
            'reason': t.reason
        } for t in self.trades])
        df.to_csv(filepath, index=False)
        print(f"✓ 交易记录: {filepath}")
    
    def export_equity_curve(self, filepath: str):
        df = pd.DataFrame({
            'timestamp': self.data['Date'].iloc[:len(self.equity_curve)],
            'equity': self.equity_curve
        })
        df.to_csv(filepath, index=False)
        print(f"✓ 权益曲线: {filepath}")
