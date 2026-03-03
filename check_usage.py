import os
from budget_service import BudgetService
from dotenv import load_dotenv
load_dotenv()
s = BudgetService()
print(f"Remaining: {s.get_remaining_quota('gemma_3_12b')}")
