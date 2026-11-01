from src.live_scan import choose_daily_decision


def test_only_best_qualified_candidate_is_selected():
    candidates = [
        {"pair": "EURUSD", "score": 0.42, "risk_pips": 10},
        {"pair": "GBPJPY", "score": 0.51, "risk_pips": 18},
        {"pair": "USDJPY", "score": 0.37, "risk_pips": 12},
    ]
    assert choose_daily_decision(candidates, 0.40)["pair"] == "GBPJPY"


def test_wait_when_no_candidate_passes_threshold():
    candidates = [{"pair": "EURUSD", "score": 0.39, "risk_pips": 9}]
    assert choose_daily_decision(candidates, 0.40) is None
