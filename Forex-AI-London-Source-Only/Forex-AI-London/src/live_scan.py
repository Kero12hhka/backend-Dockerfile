"""One-decision-per-day scanner: rank all pairs, publish only the best setup or WAIT."""
import json
from datetime import datetime, timezone

import joblib
import pandas as pd

from config import (
    PAIRS, MODEL_DIR, CAIRO_TZ, MIN_MODEL_SCORE,
    MAX_DATA_AGE_MINUTES, RISK_PCT,
)
from src.provider import fetch_bars
from src.features import build_features, FEATURES, risk_distance
from src.telegram import send_telegram


def choose_daily_decision(candidates, threshold):
    """Return exactly one trade candidate, or None when no candidate clears threshold."""
    qualified = [c for c in candidates if c["score"] is not None and c["score"] >= threshold]
    if not qualified:
        return None
    # Highest model score wins; tie-break toward the tighter stop in pip terms.
    return max(qualified, key=lambda c: (c["score"], -c["risk_pips"]))


def main(send=True):
    manifest = json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))
    rr = float(manifest["selected_rr"])
    threshold = float(manifest.get("selected_threshold", MIN_MODEL_SCORE))
    model = joblib.load(MODEL_DIR / f"model_rr_{rr:.1f}.joblib")

    now = datetime.now(timezone.utc)
    local = pd.Timestamp(now).tz_convert(CAIRO_TZ)
    lines = [
        "🤖 FOREX AI — ONE DAILY DECISION",
        f"🕘 {local:%Y-%m-%d %H:%M} Cairo | selected RR 1:{rr:g}",
        f"Maximum planned risk: {RISK_PCT:.1%} of account equity",
        "Research signals only — no auto-trading",
        "",
        "PAIR COMPARISON",
    ]
    candidates = []
    pair_rows = []

    for pair, cfg in PAIRS.items():
        try:
            bars = fetch_bars(cfg["api_symbol"])
            # Twelve Data timestamps M15 bars by their opening time. At 09:00 Cairo,
            # the 08:45 candle is the last fully closed candle.
            local_now = pd.Timestamp(now).tz_convert(CAIRO_TZ)
            decision_candle_local = local_now.normalize() + pd.Timedelta(hours=8, minutes=45)
            decision_candle_utc = decision_candle_local.tz_convert("UTC")
            bars = bars[bars.index <= decision_candle_utc]
            if bars.empty:
                raise ValueError("No completed 08:45 Cairo M15 candle")
            age = (pd.Timestamp(now) - bars.index[-1]).total_seconds() / 60
            if age > MAX_DATA_AGE_MINUTES:
                raise ValueError(f"Stale feed: latest candle is {age:.0f} minutes old")

            features = build_features(bars).dropna(subset=FEATURES[1:])
            if features.empty:
                raise ValueError("Not enough candles to calculate features")
            row = features.iloc[-1]
            price_row = bars.loc[row.name]
            atr = float(row.atr_pct * price_row.close)
            side_scores = {}
            for side, direction in ((1, "BUY"), (-1, "SELL")):
                sample = row.copy()
                sample["side"] = side
                score = float(model.predict_proba(
                    pd.DataFrame([sample[FEATURES].astype(float)])
                )[0, 1])
                side_scores[direction] = score

            direction = max(side_scores, key=side_scores.get)
            score = side_scores[direction]
            side = 1 if direction == "BUY" else -1
            entry = float(price_row.close)
            risk = risk_distance(atr, cfg)
            pip = cfg["pip"]
            candidate = {
                "pair": pair,
                "direction": direction,
                "score": score,
                "entry": entry,
                "sl": entry - side * risk,
                "tp": entry + side * rr * risk,
                "risk_pips": risk / pip,
                "pip": pip,
                "reason": "Highest-scoring model direction for this pair",
            }
            candidates.append(candidate)
            pair_rows.append((pair, direction, score, "OK"))
        except Exception as exc:
            pair_rows.append((pair, "NO DATA", None, str(exc)))

    for pair, direction, score, status in pair_rows:
        if score is None:
            lines.append(f"• {pair}: unavailable ({status})")
        else:
            lines.append(f"• {pair}: best side {direction} | score {score * 100:.1f}/100")

    decision = choose_daily_decision(candidates, threshold)
    lines.append("")
    lines.append("FINAL DAILY DECISION")
    if decision is None:
        lines += [
            "⏸ WAIT — no pair passed the model's validation threshold.",
            f"Required model score: {threshold * 100:.1f}/100",
            "No trade is the correct decision when the setup is weak or data is incomplete.",
        ]
    else:
        cfg = PAIRS[decision["pair"]]
        fmt = ".5f" if cfg["pip"] == 0.0001 else ".3f"
        lines += [
            f"🏆 SELECTED: {decision['pair']} — {decision['direction']}",
            f"Entry: {format(decision['entry'], fmt)}",
            f"Stop Loss: {format(decision['sl'], fmt)}",
            f"Take Profit: {format(decision['tp'], fmt)}",
            f"Risk/Reward: 1:{rr:g}",
            f"Stop distance: {decision['risk_pips']:.1f} pips",
            f"Model score: {decision['score'] * 100:.1f}/100 (not a calibrated win probability)",
            f"Planned maximum account risk: {RISK_PCT:.1%}",
            "Position size must be calculated using your broker's contract size and account currency.",
        ]

    lines += [
        "",
        "Prices are indicative composite quotes; broker spread/slippage may change results.",
        "Paper-trade and forward-test before considering live use. No guaranteed win rate.",
    ]
    message = "\n".join(lines)
    print(message)
    if send:
        send_telegram(message)
    return decision, pair_rows


if __name__ == "__main__":
    main()
