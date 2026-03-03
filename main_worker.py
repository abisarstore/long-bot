import time
import os
import logging
import json
from datetime import datetime, timezone
from ingest import MarketIngester, OnchainProvider, SocialProvider
from features import FeaturePipeline
from decision_engine import DecisionEngine
from models_orchestrator import ModelOrchestrator
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainWorker")

class MainWorker:
    def __init__(self, mock_mode=True):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            logger.error("SUPABASE_URL or SUPABASE_KEY missing. Fail-safe active.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)

        self.ingester = MarketIngester()
        self.onchain = OnchainProvider()
        self.social = SocialProvider()
        self.engine = DecisionEngine()
        self.orchestrator = ModelOrchestrator(mock_mode=mock_mode)

    def run_cycle(self):
        if not self.supabase:
            logger.error("Supabase not initialized. Skipping cycle.")
            return

        logger.info("Starting analysis cycle...")

        symbols = self.ingester.fetch_top_by_volume(150)
        logger.info(f"Fetched {len(symbols)} symbols from watchlist.")

        batch_size = 25
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            batch_data = []

            for symbol in batch:
                try:
                    ohlcv = self.ingester.fetch_ohlcv(symbol, limit=300)
                    pipeline = FeaturePipeline(ohlcv)
                    ta_features = pipeline.get_latest_features()

                    if 'timestamp' in ta_features:
                        ta_features['timestamp'] = str(ta_features['timestamp'])

                    batch_data.append({
                        "symbol": symbol,
                        "ta": ta_features,
                        "sent": self.social.fetch_sentiment(symbol).get('score', 50)
                    })
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol}: {e}")

            if not batch_data:
                continue

            screen_res = self.orchestrator.call_screening(batch_data)
            if not screen_res:
                continue

            results = sorted(screen_res["results"], key=lambda x: x["quick_score"], reverse=True)
            top_candidates = results[:int(len(results) * 0.2) + 1]

            for item in top_candidates:
                symbol = item["symbol"]
                logger.info(f"Running deep analysis for {symbol}")

                deep_res = self.orchestrator.call_deep_analysis(
                    symbol,
                    market_data={},
                    onchain_data=self.onchain.fetch_metrics(symbol),
                    social_data={}
                )

                if deep_res:
                    ta_info = next((x["ta"] for x in batch_data if x["symbol"] == symbol), {})

                    final = self.engine.calculate_final_score(
                        ta_info,
                        self.onchain.fetch_metrics(symbol),
                        {"score": item["quick_score"]}
                    )

                    self.supabase.table("signals").insert({
                        "symbol": symbol,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "score": final["score"],
                        "rating": final["rating"],
                        "model_version": deep_res["model_version"],
                        "prompt_hash": deep_res["prompt_hash"],
                        "payload": {
                            "screen": item,
                            "deep": deep_res["results"],
                            "breakdown": final["breakdown"]
                        }
                    }).execute()

        logger.info("Cycle completed.")

if __name__ == "__main__":
    worker = MainWorker(mock_mode=True)
    worker.run_cycle()
