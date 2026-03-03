# Operational Runbook

## Emergency Procedures
### Stop All Trading
1. Set `LIVE_MODE=false` in environment variables.
2. Restart the worker service.
3. Alternatively, update the `watchlist` table in Supabase to set `enabled=false` for all tokens.

### Budget Reset
If a model's budget is exhausted prematurely:
1. Verify the reason for high usage in `logs`.
2. Manually reset `reserved_calls` in `model_usage` for the current day if necessary.

## Monitoring
- Check `logs` table for `error` or `critical` levels.
- Monitor `model_usage` to ensure RPD limits are respected.
