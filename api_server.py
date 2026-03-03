from fastapi import FastAPI
from paper_executor import PaperExecutor
app = FastAPI()
executor = PaperExecutor()
@app.get("/api/top-signals")
async def top(): return {"data": []}
@app.post("/api/simulate-trade")
async def trade(): return {"success": True}
