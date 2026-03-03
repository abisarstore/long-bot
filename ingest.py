import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

class MarketIngester:
    def __init__(self, exchange_id='coinbase'):
        self.exchange = getattr(ccxt, exchange_id)()

    def fetch_top_by_volume(self, limit=150):
        tickers = self.exchange.fetch_tickers()
        usdt_pairs = [s for s in tickers if s.endswith('/USDT') and tickers[s].get('quoteVolume') is not None]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: tickers[x]['quoteVolume'], reverse=True)
        return sorted_pairs[:limit]

    def fetch_ohlcv(self, symbol, timeframe='5m', limit=100):
        return self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

class OnchainProvider:
    def fetch_metrics(self, symbol): return {"exchange_inflow": 0}

class SocialProvider:
    def fetch_sentiment(self, symbol): return {"score": 50}
