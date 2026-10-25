import json
from pathlib import Path
import pandas as pd
import numpy as np

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
    names = pd.Series({c:COUNTRY_ZH.get(str(c),'待补中文名称（'+str(c)+'）') for c in names.index})
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
    national_share = china.sum() / total.sum() if total.sum() else float('nan')
    out['中国份额相对全国倍数'] = (out['自华进口额（美元）'] / total.where(total.ne(0))) / national_share if national_share > 0 else float('nan')
    return out.reset_index().sort_values('进口金额（美元）', ascending=False)


COUNTRY_ZH = {
    '1220':'加拿大','1610':'圣皮埃尔和密克隆','2010':'墨西哥','2050':'危地马拉',
    '2150':'洪都拉斯','2230':'哥斯达黎加','2250':'巴拿马','2320':'百慕大',
    '2360':'巴哈马','2410':'牙买加','2430':'特克斯和凯科斯群岛','2440':'开曼群岛',
    '2470':'多米尼加共和国','2482':'英属维尔京群岛','2485':'蒙特塞拉特',
    '2720':'巴巴多斯','2740':'特立尼达和多巴哥','2777':'库拉索','2831':'瓜德罗普',
    '3010':'哥伦比亚','3310':'厄瓜多尔','3330':'秘鲁','3370':'智利',
    '3510':'巴西','3530':'巴拉圭','3550':'乌拉圭','3570':'阿根廷',
    '4000':'冰岛','4010':'瑞典','4039':'挪威','4050':'芬兰','4099':'丹麦',
    '4120':'英国','4190':'爱尔兰','4210':'荷兰','4231':'比利时','4239':'卢森堡',
    '4272':'摩纳哥','4279':'法国','4280':'德国','4330':'奥地利','4351':'捷克',
    '4359':'斯洛伐克','4370':'匈牙利','4411':'列支敦士登','4419':'瑞士',
    '4470':'爱沙尼亚','4490':'拉脱维亚','4510':'立陶宛','4550':'波兰',
    '4621':'俄罗斯','4622':'白俄罗斯','4623':'乌克兰','4633':'格鲁吉亚',
    '4641':'摩尔多瓦','4700':'西班牙','4710':'葡萄牙','4730':'马耳他',
    '4751':'圣马力诺','4759':'意大利','4791':'克罗地亚','4792':'斯洛文尼亚',
    '4794':'北马其顿','4801':'塞尔维亚','4804':'黑山','4840':'希腊',
    '4850':'罗马尼亚','4870':'保加利亚','4890':'土耳其','5081':'以色列',
    '5110':'约旦','5170':'沙特阿拉伯','5180':'卡塔尔','5200':'阿联酋',
    '5230':'阿曼','5250':'巴林','5330':'印度','5350':'巴基斯坦','5380':'孟加拉国',
    '5460':'缅甸','5490':'泰国','5520':'越南','5530':'老挝','5550':'柬埔寨',
    '5570':'马来西亚','5590':'新加坡','5600':'印度尼西亚','5650':'菲律宾',
    '5660':'中国澳门','5700':'中国','5800':'韩国','5820':'中国香港',
    '5830':'中国台湾','5880':'日本','6021':'澳大利亚','6141':'新西兰','6227':'图瓦卢',
    '7140':'摩洛哥','7290':'埃及','7420':'喀麦隆','7450':'马里','7460':'几内亚',
    '7470':'塞拉利昂','7510':'尼日尔','7550':'加蓬','7560':'乍得','7749':'埃塞俄比亚',
    '7790':'肯尼亚','7800':'塞舌尔','7830':'坦桑尼亚','7870':'莫桑比克',
    '7881':'马约特','7910':'南非','7940':'赞比亚'
}


def label_country(code, names):
    return COUNTRY_ZH.get(str(code), str(names.get(code, code)))


def concentration(shares):
    """Zeros contribute zero; entropy effective count uses fixed-universe shares."""
    hhi = shares.pow(2).sum(axis=1)
    entropy = -(shares * np.log(shares.where(shares.gt(0)))).sum(axis=1)
    return pd.DataFrame({'HHI':hhi, 'CR5（%）':shares.apply(lambda r:r.nlargest(5).sum()*100,axis=1),
                         '有效来源数（1/HHI）':1/hhi.where(hhi.gt(0)),
                         '熵有效来源数':np.exp(entropy),
                         '有贸易来源数':shares.gt(0).sum(axis=1)})


def comparison(raw, end, length):
    finish = pd.Period(end,'M')
    current = [str(p) for p in pd.period_range(finish-length+1,finish,freq='M')]
    prior = [str(p) for p in pd.period_range(finish-2*length+1,finish-length,freq='M')]
    if not set(current+prior).issubset(raw.index):
        return None
    old, new = raw.loc[prior].sum(), raw.loc[current].sum()
    result = pd.DataFrame({'基期金额':old,'报告期金额':new})
    result['金额变化'] = new-old
    result['基期份额（%）'] = old/old.sum()*100
    result['报告期份额（%）'] = new/new.sum()*100
    result['份额变化（百分点）'] = result['报告期份额（%）']-result['基期份额（%）']
    result['金额增速（%）'] = (new/old.where(old.gt(0))-1)*100
    result['对美国进口增长的贡献（百分点）'] = (new-old)/old.sum()*100
    result.index.name = 'CTY_CODE'
    return result, prior, current


def quality_summary(state, port):
    records=[]
    for name,df,geo in [('目的地州',state,'STATE'),('卸货口岸',port,'PORT')]:
        records.append({'数据表':name,'记录数':len(df),'月份数':df.time.nunique(),
                        '原产国代码数（含零记录）':df.CTY_CODE.nunique(),
                        '地区分类数':df[geo].nunique(),
                        '重复键数':int(df.duplicated(['time','CTY_CODE',geo,'I_COMMODITY']).sum()),
                        '金额大于零但海空毛重为零的记录数':int((df.GEN_VAL_MO.gt(0)&(df.VES_WGT_MO+df.AIR_WGT_MO).eq(0)).sum())})
    a=state.groupby(['time','CTY_CODE']).GEN_VAL_MO.sum()
    b=port.groupby(['time','CTY_CODE']).GEN_VAL_MO.sum()
    return pd.DataFrame(records), int(a.sub(b,fill_value=0).ne(0).sum())
