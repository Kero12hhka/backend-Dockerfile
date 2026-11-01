from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent
RAW_DIR=ROOT/"data"/"raw"; MODEL_DIR=ROOT/"models"; REPORT_DIR=ROOT/"reports"
PAIRS={
 "EURUSD":{"api_symbol":"EUR/USD","pip":0.0001,"max_sl_pips":12.0},
 "GBPUSD":{"api_symbol":"GBP/USD","pip":0.0001,"max_sl_pips":12.0},
 "GBPJPY":{"api_symbol":"GBP/JPY","pip":0.01,"max_sl_pips":20.0},
 "USDJPY":{"api_symbol":"USD/JPY","pip":0.01,"max_sl_pips":20.0},
}
RR_CANDIDATES=(2.0,2.5,3.0)
CAIRO_TZ=os.getenv("CAIRO_TIMEZONE","Africa/Cairo")
SOURCE_TZ=os.getenv("SOURCE_TIMEZONE","UTC")
MIN_MODEL_SCORE=float(os.getenv("MIN_MODEL_SCORE","0.60"))
RISK_PCT=float(os.getenv("RISK_PCT","0.01"))
MAX_DATA_AGE_MINUTES=int(os.getenv("MAX_DATA_AGE_MINUTES","45"))
LIVE_INTERVAL="15min"; LIVE_OUTPUTSIZE=600
TRAIN_END="2024-12-31 23:59:59"; VALIDATION_START="2025-01-01"
VALIDATION_END="2025-12-31 23:59:59"; TEST_START="2026-01-01"
