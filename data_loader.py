import yfinance as yf
import pandas as pd

def load_stock_data(tickers, start="2020-01-01", end=None):
    """
    تحميل البيانات التاريخية للأسهم من Yahoo Finance
    """
    data = yf.download(tickers, start=start, end=end, group_by="ticker", auto_adjust=True)
    
    # لو البيانات فيها مستوى متعدد للأعمدة نحوله لشكل بسيط
    if isinstance(data.columns, pd.MultiIndex):
        data = data.stack(level=0).rename_axis(['Date', 'Ticker']).reset_index()
    
    return data
