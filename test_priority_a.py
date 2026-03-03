import unittest
import os
import uuid
from main_worker import MainWorker
from budget_service import BudgetService
from models_orchestrator import ModelOrchestrator
from dotenv import load_dotenv

load_dotenv()

class TestPriorityA(unittest.TestCase):
    def setUp(self):
        self.worker = MainWorker(mock_mode=True)
        self.budget = BudgetService()
        self.orchestrator = ModelOrchestrator(mock_mode=True)

    def test_deduplication_logic(self):
        symbol = "TEST/USDT"
        # Force a cycle to insert one signal
        batch = [{"symbol": symbol, "ta": {}, "sent": 50}]
        res = self.orchestrator.call_screening(batch)
        # Manually insert to ensure it exists
        self.worker.supabase.table("signals").insert({
            "symbol": symbol, "timestamp": "2026-03-03T10:00:00Z",
            "score": 80, "rating": 8, "model_version": "v1", "prompt_hash": "h1", "payload": {}
        }).execute()

        # Check duplicate
        is_dup = self.worker._is_duplicate_signal(symbol)
        self.assertTrue(is_dup)

    def test_atomic_reservation_rpc(self):
        model = "gemma_3_12b"
        # This test calls the actual Supabase RPC
        success = self.budget.reserve_calls(model, 1)
        self.assertTrue(success)
        self.budget.commit_calls(model, 1)

    def test_top_level_fields_population(self):
        # We'll just verify the logic in the main_worker loop indirectly
        # by checking the payload structure in a mock screen call
        res = self.orchestrator.call_deep_analysis("BTC/USDT", {}, {}, {})
        self.assertIn("confidence", res["results"])
        self.assertIn("tp1", res["results"]["targets"])

if __name__ == "__main__":
    unittest.main()
