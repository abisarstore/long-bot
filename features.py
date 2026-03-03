import pandas as pd
import ta
import numpy as np

class FeaturePipeline:
    def __init__(self, ohlcv_data):
        self.df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='ms')

    def compute_indicators(self):
        if len(self.df) < 200:
            return self.df # Not enough data for EMA200

        self.df['ema_50'] = ta.trend.EMAIndicator(self.df['close'], window=50).ema_indicator()
        self.df['ema_200'] = ta.trend.EMAIndicator(self.df['close'], window=200).ema_indicator()
        self.df['rsi'] = ta.momentum.RSIIndicator(self.df['close'], window=14).rsi()
        self.df['macd_diff'] = ta.trend.MACD(self.df['close']).macd_diff()

        # Vol Spike
        self.df['vol_sma_24h'] = self.df['volume'].rolling(window=min(288, len(self.df))).mean()
        self.df['vol_spike'] = self.df['volume'] / self.df['vol_sma_24h']

        return self.df.dropna()

    def get_latest_features(self):
        res = self.compute_indicators()
        if res.empty:
            # Return raw values if indicators couldn't be computed
            return self.df.iloc[-1].to_dict()
        return res.iloc[-1].to_dict()
