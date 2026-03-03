import os
import json
import hashlib
import google.generativeai as genai
from budget_service import BudgetService
from dotenv import load_dotenv

load_dotenv()

class ModelOrchestrator:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        self.budget = BudgetService()
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.mock_mode and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model_12b = genai.GenerativeModel('gemini-1.5-flash') # Proxy for Gemma 12B
            self.model_27b = genai.GenerativeModel('gemini-1.5-pro')   # Proxy for Gemma 27B

    def _generate_hash(self, version, system_prompt, user_input):
        content = f"{version}{system_prompt}{json.dumps(user_input)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def call_screening(self, batch_data):
        model_key = "gemma_3_12b"
        if not self.budget.reserve_calls(model_key, 1):
            return None

        try:
            if self.mock_mode:
                # Deterministic mock based on symbol count
                results = [{"symbol": item["symbol"], "quick_score": 70, "rating": 7, "quick_label": "Bullish", "confidence": 0.8} for item in batch_data]
            else:
                # Real call logic
                prompt = f"Analyze these tokens: {json.dumps(batch_data)}"
                response = self.model_12b.generate_content(prompt)
                results = json.loads(response.text)

            self.budget.commit_calls(model_key, 1)
            return {
                "results": results,
                "model_version": "1.0.0-SCREEN",
                "prompt_hash": self._generate_hash("1.0.0-SCREEN", "system_text", batch_data)
            }
        except Exception as e:
            self.budget.rollback_reservation(model_key, 1)
            print(f"Orchestrator Error: {e}")
            return None

    def call_deep_analysis(self, symbol, market_data, onchain_data, social_data):
        model_key = "gemma_3_27b"
        if not self.budget.reserve_calls(model_key, 1):
            return None

        try:
            if self.mock_mode:
                results = {
                    "symbol": symbol, "score": 85.0, "rating": 9,
                    "thesis": "Deep mock analysis confirms breakout.",
                    "confidence": 0.9, "targets": {"entry": 100, "tp1": 110, "tp2": 120, "sl": 90},
                    "trailing_stop": {"activation_pct": 0.05, "callback_pct": 0.01},
                    "risk_assessment": "Low"
                }
            else:
                prompt = f"Deep analysis for {symbol} with data: {json.dumps(market_data)}"
                response = self.model_27b.generate_content(prompt)
                results = json.loads(response.text)

            self.budget.commit_calls(model_key, 1)
            return {
                "results": results,
                "model_version": "1.0.0-DEEP",
                "prompt_hash": self._generate_hash("1.0.0-DEEP", "system_text", symbol)
            }
        except Exception as e:
            self.budget.rollback_reservation(model_key, 1)
            return None

if __name__ == "__main__":
    orchestrator = ModelOrchestrator(mock_mode=True)
    res = orchestrator.call_screening([{"symbol": "BTC/USDT"}])
    print(f"Mock Screen: {res['results'][0]['symbol']}")
