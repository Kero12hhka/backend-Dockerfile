import os,requests
import pandas as pd
from src.data import load_live_frame
from config import LIVE_INTERVAL,LIVE_OUTPUTSIZE
def fetch_bars(symbol):
    key=os.getenv("TWELVE_DATA_API_KEY")
    if not key: raise RuntimeError("Missing TWELVE_DATA_API_KEY")
    r=requests.get("https://api.twelvedata.com/time_series",params={"symbol":symbol,"interval":LIVE_INTERVAL,
      "outputsize":LIVE_OUTPUTSIZE,"timezone":"UTC","order":"asc","apikey":key},timeout=30)
    r.raise_for_status(); p=r.json()
    if p.get("status")=="error" or "values" not in p: raise RuntimeError(f"Twelve Data: {p}")
    return load_live_frame(p["values"])
