import zipfile, pandas as pd
from config import RAW_DIR,SOURCE_TZ

def normalise(df):
    df.columns=[str(c).strip().lower() for c in df.columns]
    if "time" not in df and "datetime" in df: df=df.rename(columns={"datetime":"time"})
    if "time" not in df: raise ValueError("CSV needs time column")
    bid=[f"{c}_bid" for c in ("open","high","low","close")]
    ask=[f"{c}_ask" for c in ("open","high","low","close")]
    if all(c in df for c in bid+ask):
        out=pd.DataFrame({"time":df.time})
        for c in ("open","high","low","close"):
            out[c]=(pd.to_numeric(df[c+"_bid"],errors="coerce")+pd.to_numeric(df[c+"_ask"],errors="coerce"))/2
    else:
        out=df[["time","open","high","low","close"]].copy()
        for c in ("open","high","low","close"): out[c]=pd.to_numeric(out[c],errors="coerce")
    ts=pd.to_datetime(out.time,errors="coerce")
    if ts.dt.tz is None: ts=ts.dt.tz_localize(SOURCE_TZ,ambiguous="NaT",nonexistent="shift_forward")
    out["time"]=ts.dt.tz_convert("UTC")
    return out.dropna().sort_values("time").drop_duplicates("time").set_index("time")[["open","high","low","close"]].astype(float)

def load_pair_history(pair):
    alias=pair.lower()
    frames=[]
    # Search inside every archive: the USDJPY CSV is bundled in the GBPUSD ZIP.
    for path in RAW_DIR.iterdir():
        if path.suffix.lower()==".zip":
            with zipfile.ZipFile(path) as z:
                for name in z.namelist():
                    if name.lower().endswith(".csv") and alias in name.lower():
                        with z.open(name) as f: frames.append(normalise(pd.read_csv(f)))
        elif path.suffix.lower()==".csv" and alias in path.name.lower():
            frames.append(normalise(pd.read_csv(path)))
    if not frames: raise FileNotFoundError(f"No raw data for {pair}")
    m1=pd.concat(frames).sort_index()
    m1=m1[~m1.index.duplicated(keep="last")]
    return m1.resample("15min",label="left",closed="left").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).dropna()

def load_live_frame(values):
    df=pd.DataFrame(values).rename(columns={"datetime":"time"})
    for c in ("open","high","low","close"): df[c]=pd.to_numeric(df[c],errors="coerce")
    df["time"]=pd.to_datetime(df.time,errors="coerce",utc=True)
    return df.dropna().sort_values("time").drop_duplicates("time").set_index("time")[["open","high","low","close"]]
