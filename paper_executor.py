import os, uuid
from supabase import create_client

class PaperExecutor:
    def __init__(self): self.supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    def execute_trade(self, user_id, symbol, side, amount, price, signal_id=None):
        trade_id = str(uuid.uuid4())
        self.supabase.table("paper_trades").insert({"id": trade_id, "symbol": symbol, "side": side, "amount": amount, "entry_price": price}).execute()
        return {"success": True, "trade_id": trade_id}
