"""
数据加载和技术指标计算模块
"""
import pandas as pd
import numpy as np
from typing import Optional
import sys
sys.path.append('..')
from config import INDICATOR_CONFIG


class DataFeed:
    """数据加载和指标计算"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df: Optional[pd.DataFrame] = None
        
    def load_data(self) -> pd.DataFrame:
        """加载CSV数据"""
        self.df = pd.read_csv(self.file_path)
        
        # 标准化列名
        column_mapping = {
            'date': 'Date', 'open': 'Open', 'high': 'High',
            'low': 'Low', 'close': 'Close', 'volume': 'Volume',
            'volume btc': 'Volume', 'timestamp': 'Date',
        }
        self.df.columns = [column_mapping.get(c.lower().strip(), c) for c in self.df.columns]
        
        # 转换日期
        self.df['Date'] = pd.to_datetime(self.df['Date'], format='mixed', dayfirst=False, errors='coerce')
        
        invalid_dates = self.df['Date'].isna().sum()
        if invalid_dates > 0:
            print(f"  ⚠ 跳过 {invalid_dates} 行无效日期")
            self.df = self.df.dropna(subset=['Date'])
        
        self.df = self.df.sort_values('Date').reset_index(drop=True)
        
        for col in ['Open', 'High', 'Low', 'Close']:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        self.df = self.df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        print(f"✓ 加载 {len(self.df)} 条数据")
        print(f"  {self.df['Date'].min()} ~ {self.df['Date'].max()}")
        
        return self.df
    
    def calculate_indicators(self) -> pd.DataFrame:
        """计算技术指标"""
        df = self.df.copy()
        
        # EMA
        df['EMA_fast'] = df['Close'].ewm(span=INDICATOR_CONFIG['ema_fast'], adjust=False).mean()
        df['EMA_slow'] = df['Close'].ewm(span=INDICATOR_CONFIG['ema_slow'], adjust=False).mean()
        df['EMA_trend'] = df['Close'].ewm(span=INDICATOR_CONFIG.get('trend_ema', 100), adjust=False).mean()
        
        # ATR
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=INDICATOR_CONFIG['atr_period']).mean()
        df['ATR_pct'] = df['ATR'] / df['Close']
        
        df = df.dropna().reset_index(drop=True)
        self.df = df
        
        print(f"✓ 指标计算完成，有效数据 {len(df)} 条")
        return df
    
    def get_data(self) -> pd.DataFrame:
        if self.df is None:
            self.load_data()
            self.calculate_indicators()
        return self.df
