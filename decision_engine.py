import math

class DecisionEngine:
    def __init__(self, weights=None):
        self.weights = weights or {
            "ta": 0.45,
            "onchain": 0.25,
            "sentiment": 0.20,
            "fundamentals": 0.10
        }

    def compute_ta_score(self, features):
        """
        TA Rules:
        +1 EMA50 > EMA200
        +1 RSI between 30-60 and rising
        +1 MACD Hist positive
        -1 Price < EMA200
        """
        raw_score = 0
        if features.get('ema_50', 0) > features.get('ema_200', 0):
            raw_score += 1

        rsi = features.get('rsi', 50)
        if 30 <= rsi <= 60:
            raw_score += 1

        if features.get('macd_diff', 0) > 0:
            raw_score += 1

        if features.get('close', 0) < features.get('ema_200', 0):
            raw_score -= 1

        # Volume factor: current_volume / avg_volume_24h (clamped 0.5 to 2.0)
        vol_factor = min(2.0, max(0.5, features.get('vol_spike', 1.0)))

        # Map raw (-1 to 3) to 0-100 base
        base_score = ((raw_score + 1) / 4) * 100
        return min(100, max(0, base_score * vol_factor))

    def compute_onchain_score(self, onchain):
        """
        +2 net exchange outflow
        -2 large transfer to exchange
        """
        score = 0
        if onchain.get('exchange_inflow', 0) < 0:
            score += 2
        if onchain.get('large_transfers', 0) > 100: # BTC threshold example
            score -= 2

        return min(100, max(0, (score + 2) * 25))

    def compute_sentiment_score(self, sentiment):
        # Scale input sentiment (0-100)
        return sentiment.get('score', 50)

    def calculate_final_score(self, ta_features, onchain_data, sentiment_data, fundamental_data=None):
        ta_s = self.compute_ta_score(ta_features)
        on_s = self.compute_onchain_score(onchain_data)
        sent_s = self.compute_sentiment_score(sentiment_data)
        fund_s = 50.0 # Default fallback

        final_score = (
            ta_s * self.weights["ta"] +
            on_s * self.weights["onchain"] +
            sent_s * self.weights["sentiment"] +
            fund_s * self.weights["fundamentals"]
        )

        rating = math.ceil(final_score / 10)
        return {
            "score": round(float(final_score), 2),
            "rating": min(10, max(1, rating)),
            "breakdown": {
                "ta": round(ta_s, 2),
                "onchain": round(on_s, 2),
                "sentiment": round(sent_s, 2)
            }
        }

if __name__ == "__main__":
    # Test with bullish data
    engine = DecisionEngine()
    ta = {'ema_50': 60000, 'ema_200': 55000, 'rsi': 55, 'macd_diff': 100, 'close': 62000, 'vol_spike': 1.2}
    onchain = {'exchange_inflow': -100, 'large_transfers': 0}
    sent = {'score': 85}
    print(f"Bullish Score: {engine.calculate_final_score(ta, onchain, sent)}")
