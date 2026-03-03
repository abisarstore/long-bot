import math

class DecisionEngine:
    def calculate_final_score(self, ta, onchain, sentiment):
        score = 50
        if ta.get('ema_50', 0) > ta.get('ema_200', 0): score += 10
        if 30 <= ta.get('rsi', 50) <= 60: score += 10
        final = min(100, max(0, score))
        return {"final_score": final, "rating": math.ceil(final/10)}
