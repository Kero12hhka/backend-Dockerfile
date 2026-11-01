import json, warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from config import PAIRS,RR_CANDIDATES,MODEL_DIR,REPORT_DIR,TRAIN_END,VALIDATION_START,VALIDATION_END,TEST_START
from src.data import load_pair_history
from src.features import build_features,make_daily_samples,FEATURES

warnings.filterwarnings("ignore")
def make_model():
    return HistGradientBoostingClassifier(learning_rate=.06,max_iter=150,max_leaf_nodes=15,
        l2_regularization=2,min_samples_leaf=20,random_state=42)

def score_frame(model,frame):
    out=frame.copy()
    out["score"]=model.predict_proba(out[FEATURES].astype(float))[:,1]
    out["day"]=pd.to_datetime(out.index,utc=True).tz_convert("Africa/Cairo").date
    return out

def evaluate(model,frame,rr,threshold):
    if frame.empty: return {"trades":0,"wins":0,"win_rate":0.0,"net_r":0.0,"profit_factor":0.0}
    q=score_frame(model,frame)
    q=q[q.score>=threshold].sort_values("score",ascending=False).drop_duplicates(["day","pair"])
    if q.empty: return {"trades":0,"wins":0,"win_rate":0.0,"net_r":0.0,"profit_factor":0.0}
    wins=int(q.label.sum()); losses=len(q)-wins
    return {"trades":int(len(q)),"wins":wins,"losses":losses,
        "win_rate":round(wins/len(q),4),"net_r":round(wins*rr-losses,2),
        "profit_factor":round(wins*rr/losses,3) if losses else None,
        "mean_model_score":round(float(q.score.mean()),4)}

def choose_threshold(model,frame,rr):
    # Select confidence threshold using validation period only.
    best=None
    for threshold in np.arange(.20,.551,.01):
        metrics=evaluate(model,frame,rr,float(threshold))
        if metrics["trades"]<20: continue
        candidate=(metrics["net_r"],metrics["profit_factor"] or 0,-metrics["trades"],float(threshold),metrics)
        if best is None or candidate[:3]>best[:3]: best=candidate
    if best is None: return .60, evaluate(model,frame,rr,.60)
    return best[3],best[4]

def main():
    chunks=[]
    for pair,cfg in PAIRS.items():
        print("Loading",pair)
        bars=load_pair_history(pair); features=build_features(bars)
        for rr in RR_CANDIDATES:
            d=make_daily_samples(bars,features,cfg,rr)
            if not d.empty:
                d["pair"],d["rr"]=pair,rr
                chunks.append(d.reset_index())
        print(f"  {len(bars):,} M15 bars")
    if not chunks: raise RuntimeError("No daily samples; verify raw files and timezone.")
    data=pd.concat(chunks,ignore_index=True); data["time"]=pd.to_datetime(data.time,utc=True)
    train=data[data.time<=pd.Timestamp(TRAIN_END,tz="UTC")]
    val=data[(data.time>=pd.Timestamp(VALIDATION_START,tz="UTC"))&(data.time<=pd.Timestamp(VALIDATION_END,tz="UTC"))]
    test=data[data.time>=pd.Timestamp(TEST_START,tz="UTC")]
    if train.empty or val.empty or test.empty:
        raise RuntimeError(f"Empty time split: train={len(train)}, validation={len(val)}, test={len(test)}")
    report={"sample_counts":{"train":len(train),"validation":len(val),"test":len(test)},"rr":{}}
    best_rr,best_net=None,-1e12
    thresholds={}
    for rr in RR_CANDIDATES:
        tr,va,te=(d[d.rr==rr].set_index("time") for d in (train,val,test))
        evaluation_model=make_model().fit(tr[FEATURES].astype(float),tr.label.astype(int))
        threshold,vm=choose_threshold(evaluation_model,va,rr)
        tm=evaluate(evaluation_model,te,rr,threshold)
        thresholds[str(rr)]=threshold
        report["rr"][str(rr)]={"validation_threshold":threshold,"validation_2025":vm,"out_of_sample_2026":tm}
        if vm["trades"]>=20 and vm["net_r"]>best_net:
            best_net,best_rr=vm["net_r"],rr
    if best_rr is None: best_rr=3.0
    # Record untouched OOS results first, then fit deployment models on all historical data.
    for rr in RR_CANDIDATES:
        subset=data[data.rr==rr]
        final_model=make_model().fit(subset[FEATURES].astype(float),subset.label.astype(int))
        joblib.dump(final_model,MODEL_DIR/f"model_rr_{rr:.1f}.joblib")
    manifest={"selected_rr":best_rr,"selected_threshold":thresholds[str(best_rr)],
        "thresholds":thresholds,"features":FEATURES,
        "deployment_fit":"all historical samples available through 2026-10-23",
        "rr_selection":"2025 validation net R only","oos_test":"2026; evaluation models trained only through 2024",
        "research_only":True}
    MODEL_DIR.mkdir(exist_ok=True); REPORT_DIR.mkdir(exist_ok=True)
    (MODEL_DIR/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    report["selected_rr_from_2025_validation"]=best_rr
    report["selected_threshold"]=thresholds[str(best_rr)]
    report["note"]="OOS test metrics use models trained through 2024. Deployment model is then refit on all available history."
    (REPORT_DIR/"training_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
