-- Add bucket_15m column to signals
ALTER TABLE signals ADD COLUMN IF NOT EXISTS bucket_15m TIMESTAMP WITH TIME ZONE;

-- Create unique index for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_symbol_bucket_15m ON signals (symbol, bucket_15m);
