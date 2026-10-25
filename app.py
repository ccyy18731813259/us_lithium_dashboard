import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model import ROOT, load_version, country_panel, geography_table
import research

st.set_page_config(page_title='美国锂离子蓄电池进口观察', page_icon='🔋', layout='wide')
st.markdown('''<style>
.stApp{background:#f5f7f9}
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1510px}
h1,h2,h3{color:#19354a;letter-spacing:-.4px}
h3{font-weight:650!important;font-size:1.2rem!important;margin-top:1.2rem!important}
[data-testid="stSidebar"]{background:#edf2f5;border-right:1px solid #dce5eb}
[data-testid="stSidebar"] .block-container{padding-top:1.6rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e0e7ec;border-top:3px solid #337c93;padding:18px 16px;min-height:137px;border-radius:10px;box-shadow:0 3px 12px rgba(22,49,67,.035)}
[data-testid="stMetricValue"]{font-size:1.85rem;font-weight:650;color:#19354a;letter-spacing:-.5px}
[data-testid="stMetricLabel"]{color:#61778a;font-size:.85rem}
[data-testid="stPlotlyChart"]{background:#fff;border:1px solid #e0e7ec;border-radius:10px;padding:6px;box-shadow:0 2px 8px rgba(22,49,67,.02);margin-bottom:14px}
[data-baseweb="tab-list"]{gap:4px;background:#e9eff3;padding:5px;border-radius:10px;margin-top:19px;margin-bottom:14px}
[data-baseweb="tab"]{height:43px;padding:0 13px;border-radius:7px;color:#577084;font-weight:550}
[data-baseweb="tab"][aria-selected="true"]{background:white;color:#15576f;box-shadow:0 2px 5px rgba(22,49,67,.07)}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none}
[data-testid="stExpander"]{background:#fff;border-color:#e0e7ec;border-radius:9px}
[data-testid="stCaptionContainer"]{color:#738593;line-height:1.65}
.report-hero{background:#17394d;border-radius:14px;padding:27px 30px;color:white;margin-bottom:12px;position:relative;overflow:hidden}
.report-hero .eyebrow{font-size:12px;letter-spacing:1.6px;color:#b6d0dc;margin-bottom:11px}
.report-hero .hero-row{display:flex;align-items:center;gap:14px}
.report-hero h1{color:#fff;font-size:32px;font-weight:650;line-height:1.35;margin:0;padding:0}
.report-hero .hero-sub{color:#bdd0db;font-size:14px;margin-top:13px;line-height:1.7}
.report-hero .hero-badge{display:inline-flex;gap:8px;align-items:center;margin-top:19px;background:#244b5e;border:1px solid #426575;border-radius:20px;padding:5px 12px;font-size:12px;color:#e0edf2}
.report-hero .dot{width:6px;height:6px;background:#7fc6ae;border-radius:50%;display:inline-block}
.sidebar-brand{font-size:12px;font-weight:600;letter-spacing:2px;color:#487181;margin-bottom:20px}
.context-bar{font-size:13px;color:#5c7586;border-left:3px solid #c5a66e;padding:6px 12px;margin:10px 0 17px}
@media(max-width:700px){.report-hero{padding:22px 18px}.report-hero h1{font-size:25px}.report-hero svg{width:32px}[data-baseweb="tab-list"]{flex-wrap:wrap}[data-baseweb="tab"]{font-size:12px;padding:0 9px}.block-container{padding-left:1rem;padding-right:1rem}}
</style>''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_load(version):
    return load_version(version)


@st.cache_data(show_spinner=False)
def cached_panel(version, rolling, display_revision='zh-v3'):
    state, _, _ = cached_load(version)
    return country_panel(state, rolling)


def chart(fig):
    fig.update_layout(template='plotly_white', font={'family':'Arial, Microsoft YaHei, sans-serif', 'size':13,'color':'#526b7b'},
                      title_font={'size':16,'color':'#24485c'},paper_bgcolor='white',plot_bgcolor='white',
                      margin={'l':22, 'r':22, 't':62, 'b':32}, legend_title_text='',
                      colorway=['#337c93','#c69c5b','#5a9d8c','#8f84a6','#c47769','#7d98ae'])
    fig.update_xaxes(showgrid=False,zeroline=False,automargin=True)
    fig.update_yaxes(gridcolor='#edf1f4',zerolinecolor='#dae3e9',automargin=True)
    st.plotly_chart(fig, width='stretch',config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})


def download(df, name):
    st.download_button('下载当前明细 CSV', df.to_csv(index=False).encode('utf-8-sig'), name+'.csv', 'text/csv', key=name)


def dashboard():
    pointer = ROOT / 'data' / 'current.json'
    if not pointer.exists():
        st.error('尚未初始化数据，请先运行更新程序。')
        return
    version = json.loads(pointer.read_text(encoding='utf-8'))['version']
    state, port, meta = cached_load(version)
    st.markdown(f'''<div class="report-hero">
      <div class="eyebrow">贸易观察 / HS 850760</div>
      <div class="hero-row"><svg width="43" height="43" viewBox="0 0 44 44" fill="none" aria-hidden="true"><rect x="9" y="8" width="27" height="32" rx="5" stroke="#98cfba" stroke-width="2"/><rect x="17" y="3" width="11" height="5" rx="2" fill="#98cfba"/><path d="M24 13L16 26H23L21 34L30 21H23L24 13Z" fill="#98cfba"/></svg><h1>美国锂离子蓄电池进口观察</h1></div>
      <div class="hero-sub">从来源结构到州与口岸，观察美国进口格局与中国份额的变化。</div>
      <div class="hero-badge"><span class="dot"></span>数据截至 {meta['max_month']} &nbsp;·&nbsp; US Census Bureau</div>
    </div>''',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">🔋 进口观察</div>',unsafe_allow_html=True)
        st.header('⚙️ 观察范围')
        all_months = sorted(state.time.unique())
        start, end = st.select_slider('时间区间', options=all_months, value=(all_months[max(0,len(all_months)-36)], all_months[-1]))
        mode = st.radio('全国趋势口径', ['当月', '滚动12个月'], key='trend_mode')
        topn = st.slider('重点来源地数量', 4, 12, 8)
        st.caption('滚动口径用于全国趋势；期间排名、州与口岸按区间内金额累计。')
        st.divider()
        st.caption('来源：US Census Bureau，statehs / porths。州为申报目的地，口岸为卸货口岸。')
        st.button('↻ 刷新数据',width='stretch')
    status_path = ROOT / 'data' / 'status.json'
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding='utf-8'))
        with st.expander('🕒 数据更新记录'):
            checked=pd.Timestamp(status['last_checked']).tz_convert('Asia/Shanghai').strftime('%Y-%m-%d %H:%M')
            st.caption('最近检查：'+checked+'（北京时间）')
            if status['status'] == 'failed':
                st.warning('本次更新未完成，正在展示上一次通过校验的数据。')
            elif status['status'] == 'bootstrap_success':
                st.caption('当前为已校验的初始数据；API任务成功运行后，将接入后续月份。')
            else:st.caption('当前版本已通过数据校验。')
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
    st.caption(f'当前指标期：{latest}　·　{mode}口径')
    cols = st.columns(4)
    cols[0].metric('💰 进口额（亿美元）', f'{total.iloc[-1]/1e8:,.2f}', delta)
    cols[1].metric('🇨🇳 中国份额', f'{cs.iloc[-1]:.1%}', change)
    cols[2].metric('🌐 前五大来源地份额', f'{share.iloc[-1].nlargest(5).sum():.1%}')
    cols[3].metric('◉ 来源集中度 HHI', f'{share.iloc[-1].pow(2).sum():.3f}')
    st.markdown(f'<div class="context-bar">观察区间　{start} — {end}　 /　 原产国口径　 /　 金额以美元计</div>',unsafe_allow_html=True)
    tabs = st.tabs(['📈 总览','🌏 来源地结构','🇨🇳 中国地位','🎯 集中度与多元化','🗺️ 目的地州','⚓ 卸货口岸','📖 数据与方法'])
    selected_raw = raw.loc[start:end]
    sums = selected_raw.sum().sort_values(ascending=False)
    leaders = sums.head(topn).index.tolist()
    palette=['#337c93','#c69c5b','#5a9d8c','#8f84a6','#c47769','#7d98ae','#70896b','#a48376']
    colors = {names[c]: ('#c84b4b' if c=='5700' else palette[i % len(palette)]) for i,c in enumerate(raw.columns)}
    with tabs[0]:
        st.subheader('📈 先看进口规模')
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
        research.overview(raw,start,end,names)
    with tabs[1]:
        st.subheader('🌏 美国主要从哪里进口？')
        ranking = sums.rename('进口金额（美元）').reset_index()
        ranking['来源地'] = ranking.CTY_CODE.map(names)
        ranking['期间份额（%）'] = ranking['进口金额（美元）']/sums.sum()*100
        chart(px.bar(ranking.head(topn).iloc[::-1], x='进口金额（美元）', y='来源地', orientation='h', color='来源地', color_discrete_map=colors, title='所选期间累计进口额排名'))
        area = share[leaders].copy()
        area.columns = [names[c] for c in leaders]
        area['其他'] = share.drop(columns=leaders).sum(axis=1)
        chart(px.area(area.mul(100).reset_index().melt(id_vars='time', var_name='来源地', value_name='份额（%）'), x='time', y='份额（%）', color='来源地', color_discrete_map=colors, title=f'来源地份额变化 · {mode}'))
        research.downloadable(ranking,'country_structure')
        research.source(raw,raw_shares,names,start,end,topn)
    with tabs[2]:
        st.subheader('🇨🇳 中国份额与进口金额')
        fig=go.Figure(go.Bar(x=window.index,y=china/1e8,name='自华进口额',marker_color='#58869f'))
        fig.add_trace(go.Scatter(x=window.index,y=cs*100,name='中国份额',yaxis='y2',line={'color':'#c84b4b','width':3}))
        fig.update_layout(title=f'自华进口金额与中国份额 · {mode}',yaxis_title='亿美元',yaxis2={'title':'份额（%）','overlaying':'y','side':'right','range':[0,100]},legend={'orientation':'h'})
        chart(fig)
        prior = str(pd.Period(end,'M')-12)
        if prior in raw_shares.index:
            changes = ((raw_shares.loc[end]-raw_shares.loc[prior])*100).rename('份额同比变化（百分点）').reset_index()
            changes['来源地'] = changes.CTY_CODE.map(names)
            changes = changes.loc[changes['份额同比变化（百分点）'].abs().nlargest(topn).index].sort_values('份额同比变化（百分点）')
            chart(px.bar(changes,x='份额同比变化（百分点）',y='来源地',orientation='h',title=f'{end}较{prior}的当月份额变化'))
        st.caption('份额变化反映进口结构，不直接证明供应替代、竞争力变化或政策因果关系。')
        download(pd.DataFrame({'月份':window.index,'自华进口额（美元）':china.values,'中国份额（%）':cs.values*100}), 'china_position')
        research.china(raw,names,end)

    with tabs[3]:
        st.subheader('🎯 进口来源有多集中？')
        concentration = pd.DataFrame({'HHI':share.pow(2).sum(axis=1), 'CR5（%）':share.apply(lambda r:r.nlargest(5).sum()*100, axis=1)})
        left, right = st.columns(2)
        with left: chart(px.line(concentration.reset_index(),x='time',y='HHI', title=f'HHI · {mode}'))
        with right: chart(px.line(concentration.reset_index(),x='time',y='CR5（%）', title=f'前五大来源地份额 · {mode}'))
        st.caption('指标始终根据全部来源地计算，不将“其他”合并成一个来源地。')
        research.diversification(raw_shares,raw,names,start,end,topn)

    def geo_view(df, geo, title, key):
        st.subheader(title)
        table = geography_table(df, geo, start, end)
        if geo == 'PORT':
            mapping = df.dropna(subset=['PORT_NAME']).drop_duplicates('PORT',keep='last').set_index('PORT').PORT_NAME
            table['地区'] = table.PORT+' · '+table.PORT.map(mapping).fillna('名称待核')
        else:
            state_names=json.loads((ROOT/'state_names.json').read_text(encoding='utf-8'))
            table['地区'] = table.STATE+' · '+table.STATE.map(state_names).fillna(table.STATE)
        metric = st.selectbox('展示指标', ['进口金额（美元）','自华进口额（美元）','中国占当地进口比重（%）','占全国自华进口比重（%）','中国份额相对全国倍数'],key=key)
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
        st.caption('中国份额相对全国倍数＝当地中国份额÷全国中国份额。大于1表示当地中国份额高于全国平均，小于1则相反。它不是风险评分。')
        research.downloadable(table,key+'_detail')
        research.geographic(df,geo,raw,names,start,end,topn,key)
    with tabs[4]: geo_view(state,'STATE','🗺️ 进口申报目的地州分布','state')
    with tabs[5]:
        geo_view(port,'PORT','⚓ 卸货口岸分布','port')
        st.caption('州表与口岸表没有联合运输路线字段，不能据此推导口岸到目的州的实际流向。')
    with tabs[6]:
        st.subheader('📖 数据从哪里来，指标怎么算')
        st.markdown('''- 产品：HS六位850760，锂离子蓄电池。本项目不区分车用与其他用途。
- 国家：原产国，不等同直接发货国。中国使用Census代码5700。
- 来源地名称统一使用中文；中国台湾、中国香港、中国澳门按原始统计分类分别展示，不将统计分类等同于主权划分。
- 金额：GEN_VAL_MO，当月一般进口海关价值，美元。
- 数量：不提供件数；海空毛重不代表全部运输方式总重量，不计算电池单价。
- 地理：州为申报目的地，不能视为最终消费地；口岸为卸货口岸。
- 期间份额：期间该来源地金额合计÷期间全国金额合计。
- HHI：全部来源地份额平方和；CR5：前五大来源地份额之和。
- 数据验证：附件初始化对照附件审计；后续API更新逐月核对全国总额及两表国家月度一致性。
- 未出现的细分组合，仅在月份提取完整的前提下按零金额参与聚合。''')
        st.write('数据覆盖：'+meta['min_month']+'—'+meta['max_month'])
        st.caption('看板版本：4.0')
        research.quality(state,port)
        st.markdown('[州接口字段](https://api.census.gov/data/timeseries/intltrade/imports/statehs/variables.html) · [口岸接口字段](https://api.census.gov/data/timeseries/intltrade/imports/porths/variables.html)')
        st.caption('页面重跑或点击重新读取时检查最新版本。后台采集由GitHub Actions执行。')


dashboard()
