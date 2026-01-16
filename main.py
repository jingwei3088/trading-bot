#!/usr/bin/env python3
"""
BTC 交易机器人 - 趋势+网格混合策略
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BACKTEST_CONFIG, OUTPUT_CONFIG
from modules.data_feed import DataFeed
from modules.backtest_engine import BacktestEngine


def main():
    print("\n" + "="*60)
    print("  BTC 趋势+网格混合策略 回测系统")
    print("="*60)
    
    # 确保目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    # 加载数据
    data_file = BACKTEST_CONFIG['data_file']
    if not os.path.exists(data_file):
        print(f"✗ 数据文件不存在: {data_file}")
        print(f"  请将数据文件放到 {data_file}")
        return
    
    feed = DataFeed(data_file)
    data = feed.get_data()
    
    # 运行回测
    engine = BacktestEngine(data)
    result = engine.run(verbose=True)
    
    # 导出结果
    engine.export_trades("results/trades.csv")
    engine.export_equity_curve("results/equity_curve.csv")
    
    print("\n✓ 完成")


if __name__ == "__main__":
    main()
