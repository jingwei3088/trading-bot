#!/usr/bin/env python3
"""
下载 BTC 历史数据 (使用 yfinance)
"""
import os

try:
    import yfinance as yf
except ImportError:
    print("正在安装 yfinance...")
    os.system("pip install yfinance")
    import yfinance as yf

import pandas as pd

def download_btc_data():
    print("正在下载 BTC-USD 历史数据...")
    
    # 下载 BTC-USD 数据 (最近2年的1小时数据)
    btc = yf.Ticker("BTC-USD")
    
    # yfinance 对1小时数据有限制，最多730天
    df = btc.history(period="2y", interval="1h")
    
    if df.empty:
        print("✗ 无法获取数据，尝试日线数据...")
        df = btc.history(period="5y", interval="1d")
    
    if df.empty:
        print("✗ 下载失败")
        return
    
    # 重置索引，将日期变为列
    df = df.reset_index()
    
    # 重命名列以匹配期望格式
    df = df.rename(columns={
        'Datetime': 'Date',
        'index': 'Date'
    })
    
    # 确保有 Date 列
    if 'Date' not in df.columns:
        df['Date'] = df.index
    
    # 只保留需要的列
    columns_to_keep = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df[[col for col in columns_to_keep if col in df.columns]]
    
    # 保存到 data 文件夹
    os.makedirs("data", exist_ok=True)
    output_file = "data/btc_1h.csv"
    df.to_csv(output_file, index=False)
    
    print(f"✓ 数据已保存到 {output_file}")
    print(f"  共 {len(df)} 条记录")
    print(f"  时间范围: {df['Date'].min()} ~ {df['Date'].max()}")
    print(f"  列名: {list(df.columns)}")

if __name__ == "__main__":
    download_btc_data()
