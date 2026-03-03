import pandas as pd
import ccxt
import logging
from features import FeaturePipeline
from decision_engine import DecisionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Backtester")

class Backtester:
    def __init__(self, initial_capital=10000.00):
        self.initial_capital = initial_capital
        self.exchange = ccxt.coinbase()
        self.engine = DecisionEngine()

    def run_backtest(self, symbol, timeframe='1h', days=90):
        logger.info(f"Starting backtest for {symbol} ({days} days)...")

        # 1. Fetch Historical Data
        limit = min(days * 24, 1000)
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        pipeline = FeaturePipeline(ohlcv)
        df = pipeline.compute_indicators()

        if df.empty:
            return {"error": "Insufficient data for indicators"}

        balance = self.initial_capital
        position = 0.0
        trades = []
        equity_curve = []

        # 2. Strategy Loop
        for i in range(len(df)):
            row = df.iloc[i]
            # Mock onchain/sentiment for history
            onchain = {'exchange_inflow': 0, 'large_transfers': 0}
            sentiment = {'score': 50}

            res = self.engine.calculate_final_score(row.to_dict(), onchain, sentiment)
            rating = res['rating']
            price = row['close']

            # Entry: Rating >= 8
            if rating >= 8 and position == 0:
                risk_amount = balance * 0.02 # 2% risk
                amount = risk_amount / price
                slippage = price * 0.001
                entry_price = price + slippage
                fee = amount * entry_price * 0.0004

                if balance >= (amount * entry_price + fee):
                    position = amount
                    balance -= (amount * entry_price + fee)
                    trades.append({'time': str(row['timestamp']), 'side': 'buy', 'price': entry_price, 'amount': amount})

            # Exit: Rating <= 4
            elif rating <= 4 and position > 0:
                slippage = price * 0.001
                exit_price = price - slippage
                fee = position * exit_price * 0.0004
                balance += (position * exit_price - fee)
                trades.append({'time': str(row['timestamp']), 'side': 'sell', 'price': exit_price, 'amount': position})
                position = 0.0

            current_equity = balance + (position * price if position > 0 else 0)
            equity_curve.append({'time': str(row['timestamp']), 'equity': round(current_equity, 2)})

        # 3. Calculate Metrics
        final_equity = balance + (position * df.iloc[-1]['close'] if position > 0 else 0)
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        # Drawdown calculation
        df_equity = pd.DataFrame(equity_curve)
        df_equity['peak'] = df_equity['equity'].cummax()
        df_equity['drawdown'] = (df_equity['peak'] - df_equity['equity']) / df_equity['peak']
        max_dd = df_equity['drawdown'].max()

        return {
            "symbol": symbol,
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "trade_count": len(trades),
            "trades": trades[:10], # Sample
            "equity_curve": equity_curve[-10:] # Sample
        }

if __name__ == "__main__":
    bt = Backtester()
    result = bt.run_backtest('BTC/USDT')
    print(f"Backtest Summary: {result['total_return_pct']}% return, {result['trade_count']} trades.")
