import time
import os
import logging
import signal
from datetime import datetime, timezone, timedelta
from ingest import MarketIngester, OnchainProvider, SocialProvider
from features import FeaturePipeline
from decision_engine import DecisionEngine
from models_orchestrator import ModelOrchestrator
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainWorker")

CADENCE_MINUTES = int(os.getenv("CADENCE_MINUTES", "5"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
SIGNAL_BUCKET_MINUTES = int(os.getenv("SIGNAL_BUCKET_MINUTES", "15"))

class MainWorker:
    def __init__(self, mock_mode=True):
        self.stop = False
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            logger.error("SUPABASE_URL or SUPABASE_KEY missing.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)

        self.ingester = MarketIngester()
        self.onchain = OnchainProvider()
        self.social = SocialProvider()
        self.engine = DecisionEngine()
        self.orchestrator = ModelOrchestrator(mock_mode=mock_mode)

    def _is_duplicate_signal(self, symbol):
        if not self.supabase: return False
        # Check if a signal for this symbol exists in the last bucket
        bucket_start = datetime.now(timezone.utc) - timedelta(minutes=SIGNAL_BUCKET_MINUTES)
        res = self.supabase.table("signals").select("id").eq("symbol", symbol).gt("timestamp", bucket_start.isoformat()).execute()
        return len(res.data) > 0

    def run_cycle(self):
        if not self.supabase:
            logger.error("Supabase not initialized.")
            return

        logger.info("--- Cycle Started ---")
        symbols = self.ingester.fetch_top_by_volume(150)
        logger.info(f"Scanning {len(symbols)} symbols...")

        batch_size = 25
        for i in range(0, len(symbols), batch_size):
            if self.stop: break
            batch = symbols[i:i+batch_size]
            batch_data = []

            for symbol in batch:
                try:
                    ohlcv = self.ingester.fetch_ohlcv(symbol, limit=300)
                    pipeline = FeaturePipeline(ohlcv)
                    ta = pipeline.get_latest_features()
                    if 'timestamp' in ta: ta['timestamp'] = str(ta['timestamp'])

                    batch_data.append({
                        "symbol": symbol,
                        "ta": ta,
                        "sent": self.social.fetch_sentiment(symbol).get('score', 50)
                    })
                except Exception as e:
                    logger.debug(f"Skip {symbol}: {e}")

            if not batch_data: continue

            screen_res = self.orchestrator.call_screening(batch_data)
            if not screen_res: continue

            results = sorted(screen_res["results"], key=lambda x: x["quick_score"], reverse=True)
            top_candidates = results[:int(len(results) * 0.2) + 1]

            for item in top_candidates:
                if self.stop: break
                symbol = item["symbol"]

                if self._is_duplicate_signal(symbol):
                    logger.info(f"Skipping duplicate: {symbol}")
                    continue

                logger.info(f"Deep Analysis: {symbol}")
                deep_res = self.orchestrator.call_deep_analysis(symbol, {}, {}, {})

                if deep_res:
                    ta_info = next((x["ta"] for x in batch_data if x["symbol"] == symbol), {})
                    final = self.engine.calculate_final_score(ta_info, self.onchain.fetch_metrics(symbol), {"score": item["quick_score"]})

                    signal_body = {
                        "symbol": symbol,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "score": final["score"],
                        "rating": final["rating"],
                        "confidence": deep_res["results"].get("confidence"),
                        "short_target": str(deep_res["results"].get("targets", {}).get("tp1")),
                        "model_version": deep_res["model_version"],
                        "prompt_hash": deep_res["prompt_hash"],
                        "payload": {
                            "screen": item,
                            "deep": deep_res["results"],
                            "breakdown": final["breakdown"]
                        }
                    }

                    if DRY_RUN:
                        logger.info(f"[DRY RUN] Signal for {symbol}: {final['score']}")
                    else:
                        self.supabase.table("signals").insert(signal_body).execute()

        logger.info("--- Cycle Completed ---")

    def start_daemon(self):
        def handle_signal(sig, frame):
            logger.info("Graceful shutdown initiated...")
            self.stop = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        logger.info(f"Daemon started. Cadence: {CADENCE_MINUTES}m")
        while not self.stop:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Cycle crashed: {e}")

            if self.stop: break

            logger.info(f"Sleeping for {CADENCE_MINUTES} minutes...")
            for _ in range(CADENCE_MINUTES * 60):
                if self.stop: break
                time.sleep(1)

        logger.info("Worker stopped.")

if __name__ == "__main__":
    worker = MainWorker(mock_mode=True)
    # Run once if explicitly requested or start daemon
    if os.getenv("RUN_ONCE") == "true":
        worker.run_cycle()
    else:
        worker.start_daemon()
