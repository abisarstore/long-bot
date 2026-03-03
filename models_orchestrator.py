import os
import json
import hashlib
import logging
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Optional
from budget_service import BudgetService
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("ModelOrchestrator")

# Check environment for MOCK_MODE
MOCK_MODE_ENV = os.getenv("MOCK_MODE", "true").lower() == "true"

try:
    from google import genai
except ImportError:
    genai = None
    logger.warning("google-genai package not installed. Real calls will fail.")

class ScreenResult(BaseModel):
    symbol: str
    quick_score: float = Field(ge=0, le=100)
    rating: int = Field(ge=1, le=10)
    quick_label: str
    confidence: float = Field(ge=0, le=1)

class DeepAnalysisResult(BaseModel):
    symbol: str
    score: float = Field(ge=0, le=100)
    rating: int = Field(ge=1, le=10)
    thesis: str
    confidence: float = Field(ge=0, le=1)
    targets: Dict[str, float]
    trailing_stop: Dict[str, float]
    risk_assessment: str

class ModelOrchestrator:
    def __init__(self, mock_mode=None):
        self.mock_mode = mock_mode if mock_mode is not None else MOCK_MODE_ENV
        self.budget = BudgetService()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None

        if not self.mock_mode:
            if not self.api_key:
                logger.error("GEMINI_API_KEY missing! Defaulting to MOCK_MODE=True")
                self.mock_mode = True
            elif not genai:
                logger.error("google-genai not installed! Defaulting to MOCK_MODE=True")
                self.mock_mode = True
            else:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(">>> REAL MODEL MODE ACTIVE (Gemini API) <<<")
        else:
            logger.info("Running in MOCK MODE (No Gemini calls)")

    def _generate_hash(self, version, system_prompt, user_input):
        content = f"{version}{system_prompt}{json.dumps(user_input)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _parse_json_from_text(self, text: str):
        try:
            clean = text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean)
        except Exception as e:
            logger.error(f"JSON Parse Error: {e} | Raw Text: {text[:500]}")
            return None

    def call_screening(self, batch_data) -> Optional[Dict]:
        model_key = "gemma_3_12b"
        if not self.budget.reserve_calls(model_key, 1):
            return None

        try:
            if self.mock_mode:
                results = [{"symbol": item["symbol"], "quick_score": 75.0, "rating": 8, "quick_label": "Bullish", "confidence": 0.85} for item in batch_data]
            else:
                prompt = f"[SYSTEM] 1.0.0-SCREEN STRICT JSON ONLY. Evaluate: {json.dumps(batch_data)}"
                logger.info(f"Initiating Real Gemini Call [SCREEN] for {len(batch_data)} tokens")
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                logger.info(f"Gemini Response Received. Tokens used: {response.usage_metadata.total_token_count}")
                results = self._parse_json_from_text(response.text)
                if results: [ScreenResult(**r) for r in results]
                else: raise ValueError("Invalid JSON response")

            self.budget.commit_calls(model_key, 1)
            return {
                "results": results,
                "model_version": f"gemma_3_12b_v1.0.1_{'mock' if self.mock_mode else 'real'}",
                "prompt_hash": self._generate_hash("1.0.0-SCREEN", "v1.1", batch_data)
            }
        except Exception as e:
            self.budget.rollback_reservation(model_key, 1)
            logger.error(f"Screening logic failure: {e}")
            return None

    def call_deep_analysis(self, symbol, market_data, onchain_data, social_data) -> Optional[Dict]:
        model_key = "gemma_3_27b"
        if not self.budget.reserve_calls(model_key, 1):
            return None

        try:
            if self.mock_mode:
                results = {
                    "symbol": symbol, "score": 82.5, "rating": 8,
                    "thesis": "Confirmed mock breakout pattern.",
                    "confidence": 0.9,
                    "targets": {"entry": 100.0, "tp1": 115.0, "tp2": 125.0, "sl": 92.0},
                    "trailing_stop": {"activation_pct": 0.05, "callback_pct": 0.01},
                    "risk_assessment": "Medium"
                }
            else:
                prompt = f"[SYSTEM] 1.0.0-DEEP STRICT JSON ONLY. Symbol: {symbol}. Data: {json.dumps(market_data)}"
                logger.info(f"Initiating Real Gemini Call [DEEP] for {symbol}")
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-pro",
                    contents=prompt
                )
                logger.info(f"Gemini Response Received. Tokens used: {response.usage_metadata.total_token_count}")
                results = self._parse_json_from_text(response.text)
                if results: DeepAnalysisResult(**results)
                else: raise ValueError("Invalid JSON response")

            self.budget.commit_calls(model_key, 1)
            return {
                "results": results,
                "model_version": f"gemma_3_27b_v1.0.1_{'mock' if self.mock_mode else 'real'}",
                "prompt_hash": self._generate_hash("1.0.0-DEEP", "v1.1", symbol)
            }
        except Exception as e:
            self.budget.rollback_reservation(model_key, 1)
            logger.error(f"Deep analysis failure for {symbol}: {e}")
            return None
