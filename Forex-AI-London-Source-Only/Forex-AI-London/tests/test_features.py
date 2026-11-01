import numpy as np,pandas as pd
from src.features import build_features,FEATURES
def test_feature_builder():
    idx=pd.date_range("2024-01-01",periods=500,freq="15min",tz="UTC")
    c=1.1+np.cumsum(np.random.default_rng(2).normal(0,.0002,len(idx)))
    b=pd.DataFrame({"open":c,"high":c+.0003,"low":c-.0003,"close":c},index=idx)
    f=build_features(b)
    assert (set(FEATURES)-{"side"}).issubset(f.columns)
    assert len(f)==len(b)
