import os
from datetime import date
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

MODEL_LIMITS = {
    "gemma_3_12b": 14400,
    "gemma_3_27b": 14400,
    "gemini_3_flash": 20,
    "gemini_2_5_flash": 20,
    "gemini_2_5_flash_lite": 20
}

class BudgetService:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def _get_or_create_usage(self, model: str):
        today = date.today().isoformat()
        res = self.supabase.table("model_usage").select("*").eq("day", today).eq("model", model).execute()

        if not res.data:
            new_row = {"day": today, "model": model, "used_calls": 0, "reserved_calls": 0}
            self.supabase.table("model_usage").insert(new_row).execute()
            return new_row
        return res.data[0]

    def reserve_calls(self, model: str, count: int = 1) -> bool:
        if model not in MODEL_LIMITS:
            return False
        usage = self._get_or_create_usage(model)
        limit = MODEL_LIMITS[model]
        if (usage["used_calls"] + usage["reserved_calls"] + count) > limit:
            return False
        today = date.today().isoformat()
        self.supabase.table("model_usage").update({"reserved_calls": usage["reserved_calls"] + count}).eq("day", today).eq("model", model).execute()
        return True

    def commit_calls(self, model: str, count: int = 1):
        today = date.today().isoformat()
        usage = self._get_or_create_usage(model)
        self.supabase.table("model_usage").update({"reserved_calls": max(0, usage["reserved_calls"] - count), "used_calls": usage["used_calls"] + count}).eq("day", today).eq("model", model).execute()

    def rollback_reservation(self, model: str, count: int = 1):
        today = date.today().isoformat()
        usage = self._get_or_create_usage(model)
        self.supabase.table("model_usage").update({"reserved_calls": max(0, usage["reserved_calls"] - count)}).eq("day", today).eq("model", model).execute()

    def get_remaining_quota(self, model: str) -> int:
        usage = self._get_or_create_usage(model)
        return MODEL_LIMITS[model] - (usage["used_calls"] + usage["reserved_calls"])
