import os
import logging
from datetime import date
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("BudgetService")

MODEL_LIMITS = {
    "gemma_3_12b": 14400,
    "gemma_3_27b": 14400,
    "gemini_3_flash": 20,
    "gemini_2_5_flash": 20,
    "gemini_2_5_flash_lite": 20
}

class BudgetService:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)

    def reserve_calls(self, model: str, count: int = 1) -> bool:
        if not self.supabase or model not in MODEL_LIMITS: return False

        limit = MODEL_LIMITS[model]
        # Atomic reservation via RPC
        try:
            res = self.supabase.rpc("reserve_model_calls", {
                "p_model": model,
                "p_count": count,
                "p_limit": limit
            }).execute()

            success = res.data is True
            if not success:
                logger.warning(f"RPD Limit Reached or Lock failed for {model}!")
            return success
        except Exception as e:
            logger.error(f"RPC Reserve failed: {e}")
            return False

    def commit_calls(self, model: str, count: int = 1):
        if not self.supabase: return
        self.supabase.rpc("commit_model_calls", {"p_model": model, "p_count": count}).execute()

    def rollback_reservation(self, model: str, count: int = 1):
        if not self.supabase: return
        self.supabase.rpc("rollback_model_calls", {"p_model": model, "p_count": count}).execute()

    def get_remaining_quota(self, model: str) -> int:
        if not self.supabase: return 0
        today = date.today().isoformat()
        res = self.supabase.table("model_usage").select("*").eq("day", today).eq("model", model).execute()
        if not res.data: return MODEL_LIMITS.get(model, 0)
        usage = res.data[0]
        return MODEL_LIMITS[model] - (usage["used_calls"] + usage["reserved_calls"])
