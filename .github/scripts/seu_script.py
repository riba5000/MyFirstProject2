import yfinance as yf
import pandas as pd

ticker = 'PETR4.SA'
data = yf.download(ticker, start='2020-01-01', end='2023-01-01')
data.to_csv(f'{ticker}.csv')
print("Dados coletados e salvos.")
