import unittest
import os
import uuid
from datetime import datetime, timezone
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

    def test_deduplication_v3(self):
        symbol = f"TEST-{uuid.uuid4()}/USDT"
        now = datetime.now(timezone.utc)
        bucket = self.worker._get_bucket_15m(now)

        signal_body = {
            "symbol": symbol, "timestamp": now.isoformat(),
            "bucket_15m": bucket.isoformat(),
            "score": 80, "rating": 8, "model_version": "v1", "prompt_hash": "h1", "payload": {}
        }

        # First insert
        self.worker.supabase.table("signals").insert(signal_body).execute()

        # Second insert (should fail due to unique index)
        with self.assertRaises(Exception):
            self.worker.supabase.table("signals").insert(signal_body).execute()

    def test_atomic_reservation_rpc(self):
        model = "gemma_3_12b"
        success = self.budget.reserve_calls(model, 1)
        self.assertTrue(success)
        self.budget.commit_calls(model, 1)

    def test_top_level_fields_population(self):
        res = self.orchestrator.call_deep_analysis("BTC/USDT", {}, {}, {})
        self.assertIn("confidence", res["results"])
        self.assertIn("tp1", res["results"]["targets"])

if __name__ == "__main__":
    unittest.main()
