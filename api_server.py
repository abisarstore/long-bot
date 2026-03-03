import os
import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from paper_executor import PaperExecutor
from backtest import Backtester

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APIServer")

# Guard Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("SUPABASE_URL or SUPABASE_KEY is not set in environment.")
    # In a real prod env, we might exit, but for FastAPI we'll handle it via middleware or dependencies
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        supabase = None

app = FastAPI(title="AI Crypto Analysis Platform API")
executor = PaperExecutor()
backtester = Backtester()

class TradeRequest(BaseModel):
    user_id: str
    symbol: str
    side: str
    amount: float
    price: float
    signal_id: Optional[str] = None

@app.get("/api/health")
async def health():
    return {"status": "ok", "db_connected": supabase is not None}

@app.get("/api/top-signals")
async def get_top_signals(limit: int = 10):
    if not supabase: raise HTTPException(status_code=503, detail="Database unavailable")
    res = supabase.table("signals").select("*").order("score", desc=True).limit(limit).execute()
    return {"data": res.data}

@app.get("/api/signal/{symbol}")
async def get_signal(symbol: str):
    if not supabase: raise HTTPException(status_code=503, detail="Database unavailable")
    res = supabase.table("signals").select("*").eq("symbol", symbol).order("timestamp", desc=True).limit(1).execute()
    if not res.data: raise HTTPException(status_code=404, detail="Signal not found")
    return {"data": res.data[0]}

@app.post("/api/simulate-trade")
async def simulate_trade(req: TradeRequest):
    if not supabase: raise HTTPException(status_code=503, detail="Database unavailable")
    result = executor.execute_trade(req.user_id, req.symbol, req.side, req.amount, req.price, req.signal_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    if not supabase: raise HTTPException(status_code=503, detail="Database unavailable")
    res = supabase.table("portfolio").select("*").eq("user_id", user_id).execute()
    if not res.data: raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"data": res.data[0]}

@app.get("/api/backtest")
async def run_backtest(symbol: str = "BTC/USDT", days: int = 90):
    try:
        result = backtester.run_backtest(symbol, days=days)
        return {"data": result}
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
