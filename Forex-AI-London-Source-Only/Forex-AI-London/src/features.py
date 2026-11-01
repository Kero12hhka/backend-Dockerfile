import numpy as np, pandas as pd
from config import CAIRO_TZ
FEATURES=["side","ret1","ret4","ret16","ema20_gap","ema50_gap","ema200_gap","ema20_slope","ema50_slope",
"rsi","atr_pct","atr_ratio","adx","bb_z","bb_width","range20","range64","break_up20","break_dn20",
"break_up64","break_dn64","sweep_up","sweep_dn","body_atr","upper_wick","lower_wick","inside",
"bull_engulf","bear_engulf","bull_fvg","bear_fvg","hour_sin","hour_cos","weekday"]

def build_features(b):
    x=b.sort_index(); o,h,l,c=(x[k].astype(float) for k in ("open","high","low","close"))
    pc=c.shift(); tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    e20=c.ewm(span=20,adjust=False).mean(); e50=c.ewm(span=50,adjust=False).mean(); e200=c.ewm(span=200,adjust=False).mean()
    d=c.diff(); gain=d.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss=(-d.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=100-100/(1+gain/loss.replace(0,np.nan))
    up,down=h.diff(),-l.diff()
    pdm=up.where((up>down)&(up>0),0).ewm(alpha=1/14,adjust=False).mean()
    mdm=down.where((down>up)&(down>0),0).ewm(alpha=1/14,adjust=False).mean()
    pdi,mdi=100*pdm/atr,100*mdm/atr
    adx=(100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)).ewm(alpha=1/14,adjust=False).mean()
    ma,sd=c.rolling(20).mean(),c.rolling(20).std()
    hi20,lo20=h.shift().rolling(20).max(),l.shift().rolling(20).min()
    hi64,lo64=h.shift().rolling(64).max(),l.shift().rolling(64).min()
    cr=(h-l).replace(0,np.nan); body=c-o
    upper=h-pd.concat([o,c],axis=1).max(axis=1); lower=pd.concat([o,c],axis=1).min(axis=1)-l
    f=pd.DataFrame(index=x.index)
    f["ret1"],f["ret4"],f["ret16"]=c.pct_change(),c.pct_change(4),c.pct_change(16)
    f["ema20_gap"],f["ema50_gap"],f["ema200_gap"]=(c-e20)/atr,(c-e50)/atr,(c-e200)/atr
    f["ema20_slope"],f["ema50_slope"]=(e20-e20.shift(4))/atr,(e50-e50.shift(16))/atr
    f["rsi"]=rsi/100; f["atr_pct"]=atr/c; f["atr_ratio"]=atr/atr.rolling(96).median(); f["adx"]=adx/100
    f["bb_z"]=(c-ma)/(2*sd); f["bb_width"]=4*sd/ma
    f["range20"]=(c-lo20)/(hi20-lo20); f["range64"]=(c-lo64)/(hi64-lo64)
    f["break_up20"],f["break_dn20"]=(c-hi20)/atr,(lo20-c)/atr
    f["break_up64"],f["break_dn64"]=(c-hi64)/atr,(lo64-c)/atr
    f["sweep_up"]=((h>hi20)&(c<hi20)).astype(float); f["sweep_dn"]=((l<lo20)&(c>lo20)).astype(float)
    f["body_atr"]=body/atr; f["upper_wick"]=upper/cr; f["lower_wick"]=lower/cr
    f["inside"]=((h<h.shift())&(l>l.shift())).astype(float)
    f["bull_engulf"]=((c>o)&(c.shift()<o.shift())&(c>=o.shift())&(o<=c.shift())).astype(float)
    f["bear_engulf"]=((c<o)&(c.shift()>o.shift())&(c<=o.shift())&(o>=c.shift())).astype(float)
    f["bull_fvg"]=(l>h.shift(2)).astype(float); f["bear_fvg"]=(h<l.shift(2)).astype(float)
    local=x.index.tz_convert(CAIRO_TZ); hour=local.hour+local.minute/60
    f["hour_sin"],f["hour_cos"]=np.sin(2*np.pi*hour/24),np.cos(2*np.pi*hour/24)
    f["weekday"]=local.dayofweek/6
    return f.replace([np.inf,-np.inf],np.nan)

def risk_distance(atr,pair):
    pip=pair["pip"]
    return min(max(float(atr)*1.5,4*pip),pair["max_sl_pips"]*pip)

def make_daily_samples(bars,features,pair,rr):
    local=bars.index.tz_convert(CAIRO_TZ)
    pos=np.flatnonzero((local.hour==8)&(local.minute==45))
    pos=pos[(pos>=330)&(pos<len(bars)-33)]
    hi,lo,op=bars.high.to_numpy(),bars.low.to_numpy(),bars.open.to_numpy()
    atr=(features.atr_pct*bars.close).to_numpy(); rows=[]
    for i in pos:
        ft=features.iloc[i]
        if not np.isfinite(atr[i]) or not np.isfinite(ft.dropna().to_numpy(dtype=float)).all(): continue
        risk=risk_distance(atr[i],pair); entry=op[i+1]
        for side in (1,-1):
            tp,sl=entry+side*rr*risk,entry-side*risk; label=0
            for j in range(i+1,min(i+33,len(bars))):
                hit_tp,hit_sl=(hi[j]>=tp,lo[j]<=sl) if side==1 else (lo[j]<=tp,hi[j]>=sl)
                if hit_tp or hit_sl:
                    label=int(hit_tp and not hit_sl); break
            row={"time":bars.index[i],"side":side,"label":label}
            row.update(ft.to_dict()); rows.append(row)
    return pd.DataFrame(rows).set_index("time") if rows else pd.DataFrame()
