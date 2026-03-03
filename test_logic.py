from decision_engine import DecisionEngine
import pytest

def test_formula():
    engine = DecisionEngine()
    ta = {'ema_50': 200, 'ema_200': 100, 'rsi': 45, 'macd_diff': 1, 'close': 210, 'vol_spike': 1.5}
    res = engine.calculate_final_score(ta, {}, {})
    assert res['score'] > 50
