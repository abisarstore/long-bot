import hashlib, json
from budget_service import BudgetService

class ModelOrchestrator:
    def __init__(self): self.budget = BudgetService()
    def call_screening(self, batch):
        if self.budget.reserve_calls("gemma_3_12b"):
            self.budget.commit_calls("gemma_3_12b")
            return {"results": [{"symbol": b["symbol"], "quick_score": 70, "rating": 7} for b in batch], "model_version": "1.0.0", "prompt_hash": "abc"}
    def call_deep_analysis(self, symbol, m, o, s):
        if self.budget.reserve_calls("gemma_3_27b"):
            self.budget.commit_calls("gemma_3_27b")
            return {"results": {"score": 80}}
