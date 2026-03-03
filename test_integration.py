import unittest
from budget_service import BudgetService
class TestBudget(unittest.TestCase):
    def test_res(self):
        s = BudgetService()
        self.assertTrue(s.reserve_calls("gemma_3_12b"))
if __name__ == "__main__": unittest.main()
