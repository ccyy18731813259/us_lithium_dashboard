import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model import ROOT, load_version, country_panel, geography_table

st.set_page_config(page_title='美国锂离子蓄电池进口观察', page_icon='🔋', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem;max-width:1480px}
h1{font-weight:700;letter-spacing:-1px;color:#102a43}
[data-testid="stMetric"]{background:#f0f5fa;border:1px solid #dce6ef;padding:16px;border-radius:8px}
[data-testid="stSidebar"]{background:#f5f7fa}
</style>''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_load(version):
    return load_version(version)


@st.cache_data(show_spinner=False)
def cached_panel(version, rolling):
    state, _, _ = cached_load(version)
    return country_panel(state, rolling)


def chart(fig):
    fig.update_layout(template='plotly_white', font={'family':'Arial, sans-serif', 'size':13},
                      margin={'l':15, 'r':15, 't':45, 'b':25}, legend_title_text='',
                      colorway=['#1f5c99','#e49c37','#278c88','#8767ad','#d56d69','#657b91'])
    st.plotly_chart(fig, width='stretch')


def download(df, name):
    st.download_button('下载当前明细 CSV', df.to_csv(index=False).encode('utf-8-sig'), name+'.csv', 'text/csv', key=name)


def dashboard():
    pointer = ROOT / 'data' / 'current.json'
    if not pointer.exists():
        st.error('尚未初始化数据，请先运行更新程序。')
        return
    version = json.loads(pointer.read_text(encoding='utf-8'))['version']
    state, port, meta = cached_load(version)
    st.title('美国锂离子蓄电池进口观察')
    st.caption(f"HS 850760 · 原产国口径 · 一般进口海关价值（美元） · 数据截至 {meta['max_month']}")
    with st.sidebar:
        st.header('观察范围')
        all_months = sorted(state.time.unique())
        start, end = st.select_slider('时间区间', options=all_months, value=(all_months[max(0,len(all_months)-36)], all_months[-1]))
        mode = st.radio('全国趋势口径', ['当月', '滚动12个月'])
        topn = st.slider('重点来源地数量', 4, 12, 8)
        st.caption('期间排名、州及口岸分布按所选区间的原始月度金额合计；滚动口径仅用于全国趋势。')
        st.divider()
        st.caption('来源：US Census Bureau，statehs / porths。州为申报目的地，口岸为卸货口岸。')
        st.button('重新读取最新版本')
    status_path = ROOT / 'data' / 'status.json'
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding='utf-8'))
        st.caption('最近检查：'+status['last_checked']+'（UTC）')
        if status['status'] == 'failed':
            st.warning('最近一次采集未完成，当前展示上一版有效数据。')
        elif status['status'] == 'bootstrap_success':
            st.info('当前为已校验的附件数据快照。配置云端API任务后才能持续获取新月份。')
    wide, shares, names = cached_panel(version, mode == '滚动12个月')
    raw, raw_shares, _ = cached_panel(version, False)
    window = wide.loc[start:end]
    if window.empty:
        st.warning('该区间没有完整12个月窗口，请扩大区间或选择当月口径。')
        return
    share = shares.loc[window.index]
    latest = window.index[-1]
    total = window.sum(axis=1)
    china = window.get('5700', pd.Series(0, index=window.index))
    cs = share.get('5700', pd.Series(0, index=share.index))
    prev = str(pd.Period(latest, 'M')-12)
    prev_total = wide.loc[prev].sum() if prev in wide.index else None
    delta = f'{(total.iloc[-1]/prev_total-1)*100:+.1f}% 同比' if prev_total else None
    change = f'{(cs.iloc[-1]-shares.loc[prev,"5700"])*100:+.1f} 个百分点同比' if prev in shares.index and '5700' in shares else None
    cols = st.columns(4)
    cols[0].metric(f'{latest} {mode}进口额', f'{total.iloc[-1]/1e8:,.2f} 亿美元', delta)
    cols[1].metric('中国份额', f'{cs.iloc[-1]:.1%}', change)
    cols[2].metric('前五大来源地份额', f'{share.iloc[-1].nlargest(5).sum():.1%}')
    cols[3].metric('来源集中度 HHI', f'{share.iloc[-1].pow(2).sum():.3f}')
    tabs = st.tabs(['总览','来源地结构','中国地位','目的地州','卸货口岸','数据与方法'])
    selected_raw = raw.loc[start:end]
    sums = selected_raw.sum().sort_values(ascending=False)
    leaders = sums.head(topn).index.tolist()
    colors = {names[c]: ('#c84b4b' if c=='5700' else px.colors.qualitative.Safe[i % 11]) for i,c in enumerate(leaders)}
    with tabs[0]:
        st.subheader('进口规模与结构')
        chart(px.line(total.rename('进口额（亿美元）').div(1e8).reset_index(), x='time', y='进口额（亿美元）', title=f'美国进口金额 · {mode}'))
        growth = wide.sum(axis=1).pct_change(12, fill_method=None).loc[start:end]*100
        chart(px.bar(growth.rename('同比（%）').reset_index(), x='time', y='同比（%）', title='进口金额同比变化'))
        st.caption('同比按上年同月比较；完整历史上先计算滚动值，再截取展示区间。')
        annual = raw.sum(axis=1).rename('进口额（美元）').reset_index()
        annual['年份'] = annual.time.str[:4]
        annual['月份'] = annual.time.str[5:]
        ytd = st.checkbox('年度比较统一到最新年份的已发布月份', value=True)
        if ytd:
            annual = annual[annual['月份'] <= meta['max_month'][5:]]
        yearly = annual.groupby('年份', as_index=False)['进口额（美元）'].sum()
        yearly['期间'] = yearly['年份'] + (f"年1—{int(meta['max_month'][5:])}月" if ytd else '年')
        if not ytd:
            yearly.loc[yearly['年份']==meta['max_month'][:4], '期间'] += f"（截至{int(meta['max_month'][5:])}月）"
        chart(px.bar(yearly, x='期间', y='进口额（美元）', title='全历史年度金额（独立于区间筛选）'))
    with tabs[1]:
        st.subheader('美国从哪些来源地进口？')
        ranking = sums.rename('进口金额（美元）').reset_index()
        ranking['来源地'] = ranking.CTY_CODE.map(names)
        ranking['期间份额（%）'] = ranking['进口金额（美元）']/sums.sum()*100
        chart(px.bar(ranking.head(topn).iloc[::-1], x='进口金额（美元）', y='来源地', orientation='h', color='来源地', color_discrete_map=colors, title='所选期间累计进口额排名'))
        area = share[leaders].copy()
        area.columns = [names[c] for c in leaders]
        area['其他'] = share.drop(columns=leaders).sum(axis=1)
        chart(px.area(area.mul(100).reset_index().melt(id_vars='time', var_name='来源地', value_name='份额（%）'), x='time', y='份额（%）', color='来源地', color_discrete_map=colors, title=f'来源地份额变化 · {mode}'))
        concentration = pd.DataFrame({'HHI':share.pow(2).sum(axis=1), 'CR5（%）':share.apply(lambda r:r.nlargest(5).sum()*100, axis=1)})
        left, right = st.columns(2)
        with left: chart(px.line(concentration.reset_index(),x='time',y='HHI', title='HHI：基于全部来源地计算'))
        with right: chart(px.line(concentration.reset_index(),x='time',y='CR5（%）', title='前五大来源地份额'))
        st.dataframe(ranking, hide_index=True, width='stretch')
        download(ranking, 'country_structure')
    with tabs[2]:
        st.subheader('中国在美国进口结构中的位置')
        chart(px.line(cs.mul(100).rename('中国份额（%）').reset_index(), x='time',y='中国份额（%）', title=f'中国份额走势 · {mode}'))
        chart(px.bar(china.div(1e8).rename('自华进口额（亿美元）').reset_index(), x='time',y='自华进口额（亿美元）', title=f'美国自中国进口金额 · {mode}'))
        prior = str(pd.Period(end,'M')-12)
        if prior in raw_shares.index:
            changes = ((raw_shares.loc[end]-raw_shares.loc[prior])*100).rename('份额同比变化（百分点）').reset_index()
            changes['来源地'] = changes.CTY_CODE.map(names)
            changes = changes.loc[changes['份额同比变化（百分点）'].abs().nlargest(topn).index].sort_values('份额同比变化（百分点）')
            chart(px.bar(changes,x='份额同比变化（百分点）',y='来源地',orientation='h',title=f'{end}较{prior}的当月份额变化'))
        st.caption('份额变化反映进口结构，不直接证明供应替代、竞争力变化或政策因果关系。')
        download(pd.DataFrame({'月份':window.index,'自华进口额（美元）':china.values,'中国份额（%）':cs.values*100}), 'china_position')

    def geo_view(df, geo, title, key):
        st.subheader(title)
        table = geography_table(df, geo, start, end)
        if geo == 'PORT':
            mapping = df.dropna(subset=['PORT_NAME']).drop_duplicates('PORT',keep='last').set_index('PORT').PORT_NAME
            table['地区'] = table.PORT+' · '+table.PORT.map(mapping).fillna('名称待核')
        else:
            table['地区'] = table.STATE
        metric = st.selectbox('展示指标', ['进口金额（美元）','自华进口额（美元）','中国占当地进口比重（%）','占全国自华进口比重（%）'],key=key)
        minimum = st.number_input('排名最低当地进口额（美元）', min_value=0, value=0, step=1000000, key=key+'_min')
        eligible = table[table['进口金额（美元）']>=minimum]
        chart(px.bar(eligible.nlargest(15, metric).sort_values(metric), x=metric,y='地区',orientation='h',title=f'{start}—{end} · Top 15'))
        if geo == 'STATE':
            mapped = table[~table.STATE.isin(['PR','VI','XX'])]
            fig = go.Figure(go.Choropleth(locations=mapped.STATE, z=mapped[metric],locationmode='USA-states',colorscale='Blues',colorbar_title=metric))
            fig.update_geos(scope='usa')
            fig.update_layout(title='美国州级分布')
            chart(fig)
            st.caption('PR、VI、XX单列保留在明细和全国分母中。地图底图需要浏览器能够加载Plotly地理资源。')
        st.caption('中国占当地进口比重：当地自华进口额÷当地全部进口额；占全国自华进口比重：当地自华进口额÷全国自华进口额。')
        st.dataframe(table, hide_index=True, width='stretch')
        download(table,key+'_detail')
    with tabs[3]: geo_view(state,'STATE','进口申报目的地州分布','state')
    with tabs[4]:
        geo_view(port,'PORT','卸货口岸分布','port')
        st.caption('州表与口岸表没有联合运输路线字段，不能据此推导口岸到目的州的实际流向。')
    with tabs[5]:
        st.subheader('数据来源与统计方法')
        st.markdown('''- 产品：HS六位850760，锂离子蓄电池。本项目不区分车用与其他用途。
- 国家：原产国，不等同直接发货国。中国使用Census代码5700。
- 金额：GEN_VAL_MO，当月一般进口海关价值，美元。
- 数量：不提供件数；海空毛重不代表全部运输方式总重量，不计算电池单价。
- 地理：州为申报目的地，不能视为最终消费地；口岸为卸货口岸。
- 期间份额：期间该来源地金额合计÷期间全国金额合计。
- HHI：全部来源地份额平方和；CR5：前五大来源地份额之和。
- 数据验证：附件初始化对照附件审计；后续API更新逐月核对全国总额及两表国家月度一致性。
- 未出现的细分组合，仅在月份提取完整的前提下按零金额参与聚合。''')
        st.write('当前版本信息', meta)
        st.markdown('[州接口字段](https://api.census.gov/data/timeseries/intltrade/imports/statehs/variables.html) · [口岸接口字段](https://api.census.gov/data/timeseries/intltrade/imports/porths/variables.html)')
        st.caption('页面重跑或点击重新读取时检查最新版本。后台采集由GitHub Actions执行。')


dashboard()
