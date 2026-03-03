import unittest
import os
import uuid
from decision_engine import DecisionEngine
from budget_service import BudgetService
from paper_executor import PaperExecutor
from dotenv import load_dotenv

load_dotenv()

class TestProductionLogic(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()
        self.budget = BudgetService()
        self.executor = PaperExecutor()

    def test_scoring_boundaries(self):
        ta = {'ema_50': 200, 'ema_200': 100, 'rsi': 45, 'macd_diff': 1, 'close': 210, 'vol_spike': 1.5}
        res = self.engine.calculate_final_score(ta, {}, {})
        self.assertGreater(res['score'], 50)
        self.assertGreaterEqual(res['rating'], 6)

        ta_bear = {'ema_50': 50, 'ema_200': 100, 'rsi': 70, 'macd_diff': -1, 'close': 40, 'vol_spike': 0.5}
        res_bear = self.engine.calculate_final_score(ta_bear, {}, {})
        self.assertLess(res_bear['score'], 50)
        self.assertLessEqual(res_bear['rating'], 4)

    def test_budget_logic(self):
        model = "gemini_3_flash"
        init = self.budget.get_remaining_quota(model)
        self.budget.reserve_calls(model, 1)
        after = self.budget.get_remaining_quota(model)
        self.assertEqual(init - 1, after)
        self.budget.rollback_reservation(model, 1)
        self.assertEqual(init, self.budget.get_remaining_quota(model))

    def test_paper_trade_slippage(self):
        # Use a random UUID to avoid conflicts
        user_id = str(uuid.uuid4())
        entry_price = 1000.0
        res = self.executor.execute_trade(user_id, 'SOL/USDT', 'buy', 1.0, entry_price)
        self.assertTrue(res['success'])
        self.assertAlmostEqual(res['adjusted_price'], 1001.0)

if __name__ == "__main__":
    unittest.main()
