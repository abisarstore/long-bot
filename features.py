import pandas as pd
import ta

class FeaturePipeline:
    def __init__(self, ohlcv_data):
        self.df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='ms')

    def compute_indicators(self):
        self.df['ema_50'] = ta.trend.EMAIndicator(self.df['close'], window=50).ema_indicator()
        self.df['ema_200'] = ta.trend.EMAIndicator(self.df['close'], window=200).ema_indicator()
        self.df['rsi'] = ta.momentum.RSIIndicator(self.df['close'], window=14).rsi()
        self.df['macd_diff'] = ta.trend.MACD(self.df['close']).macd_diff()
        self.df['vol_sma_24h'] = self.df['volume'].rolling(window=288).mean()
        self.df['vol_spike'] = self.df['volume'] / self.df['vol_sma_24h']
        return self.df.dropna()

    def get_latest_features(self):
        return self.compute_indicators().iloc[-1].to_dict()
