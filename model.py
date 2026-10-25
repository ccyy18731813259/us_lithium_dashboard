import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent


def load_version(version):
    folder = ROOT / 'data' / 'versions' / version
    return (pd.read_parquet(folder / 'statehs.parquet'),
            pd.read_parquet(folder / 'porths.parquet'),
            json.loads((folder / 'metadata.json').read_text(encoding='utf-8')))


def country_panel(state, rolling=False):
    panel = state.groupby(['time', 'CTY_CODE', 'CTY_NAME'], as_index=False).GEN_VAL_MO.sum()
    names = panel.drop_duplicates('CTY_CODE', keep='last').set_index('CTY_CODE').CTY_NAME
    wide = panel.pivot_table(index='time', columns='CTY_CODE', values='GEN_VAL_MO', aggfunc='sum', fill_value=0)
    wide = wide.reindex([str(p) for p in pd.period_range(wide.index.min(), wide.index.max(), freq='M')])
    if rolling:
        wide = wide.rolling(12, min_periods=12).sum().dropna(how='all')
    total = wide.sum(axis=1)
    share = wide.div(total.where(total.ne(0)), axis=0)
    return wide, share, names


def geography_table(df, geo, start, end):
    f = df[df.time.between(start, end)]
    total = f.groupby(geo).GEN_VAL_MO.sum().rename('进口金额（美元）')
    china = f[f.CTY_CODE == '5700'].groupby(geo).GEN_VAL_MO.sum()
    out = total.to_frame()
    out['自华进口额（美元）'] = china.reindex(out.index, fill_value=0)
    out['占全国进口比重（%）'] = total / total.sum() * 100 if total.sum() else float('nan')
    out['中国占当地进口比重（%）'] = out['自华进口额（美元）'] / total.where(total.ne(0)) * 100
    out['占全国自华进口比重（%）'] = out['自华进口额（美元）'] / china.sum() * 100 if china.sum() else float('nan')
    return out.reset_index().sort_values('进口金额（美元）', ascending=False)
