import os
import uuid
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("PaperExecutor")

class PaperExecutor:
    def __init__(self, initial_capital=10000.00):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)
        self.initial_capital = initial_capital

    def _get_portfolio(self, user_id):
        if not self.supabase: return {"balance": self.initial_capital}
        res = self.supabase.table("portfolio").select("*").eq("user_id", user_id).execute()
        if not res.data:
            new_port = {"user_id": user_id, "balance": self.initial_capital, "equity_curve": []}
            self.supabase.table("portfolio").insert(new_port).execute()
            return new_port
        return res.data[0]

    def execute_trade(self, user_id, symbol, side, amount, price, signal_id=None):
        if not self.supabase: return {"success": False, "error": "DB Uninitialized"}

        portfolio = self._get_portfolio(user_id)
        balance = float(portfolio["balance"])

        slippage_pct = 0.001
        adjusted_price = float(price * (1 + slippage_pct)) if side == 'buy' else float(price * (1 - slippage_pct))
        fees = float(amount * adjusted_price * 0.0004)

        cost = float(amount * adjusted_price + fees)

        if side == 'buy' and cost > balance:
            return {"success": False, "error": "Insufficient virtual balance"}

        trade_id = str(uuid.uuid4())
        trade_data = {
            "id": trade_id,
            "signal_id": signal_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "entry_price": adjusted_price,
            "slippage": slippage_pct,
            "fees": fees,
            "status": "open"
        }

        self.supabase.table("paper_trades").insert(trade_data).execute()

        new_balance = balance - cost if side == 'buy' else balance + (amount * adjusted_price - fees)
        self.supabase.table("portfolio").update({"balance": new_balance}).eq("user_id", user_id).execute()

        return {
            "success": True,
            "trade_id": trade_id,
            "adjusted_price": round(adjusted_price, 8),
            "fees": round(fees, 8),
            "new_balance": round(new_balance, 2)
        }
