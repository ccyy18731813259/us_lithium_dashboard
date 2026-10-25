"""Additional research views. All comparisons use raw monthly amounts."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model import ROOT, label_country, comparison, concentration, quality_summary


def chart(fig):
    fig.update_layout(template='plotly_white',font={'family':'Arial, sans-serif','size':13},
                      margin={'l':15,'r':15,'t':48,'b':25},legend_title_text='',
                      colorway=['#28749e','#329d92','#b38b35','#8065a6','#d47758','#5f86bb'])
    st.plotly_chart(fig,width='stretch')


def downloadable(df,key):
    with st.expander('查看分析明细与下载'):
        st.dataframe(df,hide_index=True,width='stretch')
        st.download_button('下载 CSV',df.to_csv(index=False).encode('utf-8-sig'),key+'.csv','text/csv',key=key)


def compare_control(raw,end,key):
    k=st.selectbox('每段比较月份数',[3,6,12],index=2,key=key)
    value=comparison(raw,end,k)
    if value is None:
        st.info('历史月份不足以形成两个完整比较区间，请选择较晚的结束月份。')
        return None
    result,old,new=value
    st.caption(f'报告期 {new[0]}—{new[-1]}；基期 {old[0]}—{old[-1]}。两段等长、不重叠；以所选末月为终点，独立于区间起点。')
    return result,old,new


def overview(raw,start,end,names):
    st.divider()
    st.subheader('周期观察：月度变化是否只是长期规模增长？')
    f=raw.loc[start:end].sum(axis=1).rename('金额').reset_index()
    f['年份']=f.time.str[:4];f['月份']=f.time.str[5:].astype(int)
    left,right=st.columns(2)
    heat=f.pivot(index='年份',columns='月份',values='金额').reindex(columns=range(1,13))/1e8
    with left:chart(px.imshow(heat,aspect='auto',color_continuous_scale='Blues',labels={'color':'亿美元'},title='年份 × 月份进口额（缺期留白）'))
    full=f.groupby('年份').月份.nunique()
    seasonal=f[f['年份'].isin(full[full.eq(12)].index)].copy()
    if not seasonal.empty:
        seasonal['相对年均月度金额（%）']=seasonal['金额']/seasonal.groupby('年份')['金额'].transform('mean')*100
        with right:chart(px.box(seasonal,x='月份',y='相对年均月度金额（%）',points='all',hover_data=['年份'],title='完整年份的季节分布'))
    else:
        with right:st.info('区间中无完整年份，暂不展示季节分布。')
    st.caption('季节图每年先除以当年月均金额，减少长期规模差异；不足12个月的年份排除。该分布不等同经统计检验的季节性规律。')
    amounts=raw.loc[start:end].sum().sort_values(ascending=False)
    leaders=', '.join(label_country(c,names) for c in amounts.head(3).index)
    st.info(f'所选期间累计进口 {amounts.sum()/1e8:,.2f} 亿美元；前三大来源地为{leaders}，合计 {amounts.head(3).sum()/amounts.sum():.1%}；中国期间份额为 {amounts.get("5700",0)/amounts.sum():.1%}。')


def source(raw,shares,names,start,end,topn):
    st.divider();st.subheader('结构变化：金额与份额是否同向？')
    labels={c:label_country(c,names) for c in raw.columns}
    leaders=raw.loc[start:end].sum().nlargest(topn).index
    ranks=raw.rank(axis=1,ascending=False,method='min').loc[start:end,leaders].rename(columns=labels)
    fig=px.line(ranks.reset_index().melt(id_vars='time',var_name='来源地',value_name='排名'),x='time',y='排名',color='来源地',title='主要来源地月度排名轨迹（同额并列）')
    fig.update_yaxes(autorange='reversed',dtick=1)
    chart(fig)
    result=compare_control(raw,end,'source_comparison')
    if result is not None:
        changes,old,new=result
        f=changes.reset_index();f['来源地']=f.CTY_CODE.map(labels)
        left,right=st.columns(2)
        big=f.loc[f['金额变化'].abs().nlargest(topn).index].sort_values('金额变化')
        with left:chart(px.bar(big,x='金额变化',y='来源地',orientation='h',color='金额变化',color_continuous_scale='RdBu',color_continuous_midpoint=0,title='金额增减最大的来源地'))
        big=f.loc[f['份额变化（百分点）'].abs().nlargest(topn).index].sort_values('份额变化（百分点）')
        with right:chart(px.bar(big,x='份额变化（百分点）',y='来源地',orientation='h',color='份额变化（百分点）',color_continuous_scale='RdBu',color_continuous_midpoint=0,title='份额增减最大的来源地'))
        plot=f.nlargest(max(topn,12),'报告期金额').copy()
        plot['报告期金额（亿美元）']=plot['报告期金额']/1e8
        chart(px.scatter(plot,x='金额增速（%）',y='份额变化（百分点）',size='报告期金额（亿美元）',hover_name='来源地',size_max=55,title='增长与份额的四象限观察（气泡为报告期金额）'))
        st.caption('横轴缺失表示基期金额为零，不能计算百分比增速。图中同向变化不代表因果替代。')
        downloadable(f,'source_deep_changes')
    selected=st.multiselect('自选来源地比较',list(raw.columns),default=leaders[:min(4,len(leaders))].tolist(),format_func=lambda c:labels[c])
    scale=st.radio('对比尺度',['金额（亿美元）','份额（%）','首月=100'],horizontal=True,key='source_scale')
    if selected:
        f=raw.loc[start:end,selected]
        if scale=='金额（亿美元）':f=f/1e8
        elif scale=='份额（%）':f=shares.loc[start:end,selected]*100
        else:f=f.div(f.iloc[0].where(f.iloc[0].gt(0)),axis=1)*100
        chart(px.line(f.rename(columns=labels).reset_index().melt(id_vars='time',var_name='来源地',value_name=scale),x='time',y=scale,color='来源地',title='自选来源地走势（原始当月数据）'))
        if scale=='首月=100':st.caption('首月没有进口的来源地不绘制指数，不用零值作为除数。')


def china(raw,names,end):
    st.divider();st.subheader('自华进口变化：美国市场规模与中国份额分别变化了多少？')
    result=compare_control(raw,end,'china_comparison')
    if result is None:return
    changes,old,new=result
    row=changes.loc['5700'];oldtotal=changes['基期金额'].sum();newtotal=changes['报告期金额'].sum()
    scale=row['基期金额']/oldtotal*(newtotal-oldtotal)
    structure=newtotal*(row['报告期金额']/newtotal-row['基期金额']/oldtotal)
    a,b,c=st.columns(3)
    a.metric('报告期自华金额（亿美元）',f'{row["报告期金额"]/1e8:,.2f}',f'{row["金额变化"]/1e8:+.2f} 亿美元')
    b.metric('报告期中国份额',f'{row["报告期份额（%）"]:.1f}%',f'{row["份额变化（百分点）"]:+.1f} 个百分点')
    c.metric('对美国进口增长的贡献',f'{row["对美国进口增长的贡献（百分点）"]:+.1f} 个百分点')
    fig=go.Figure(go.Waterfall(x=['基期自华额','美国总进口规模项','中国份额变化项','报告期自华额'],y=[row['基期金额']/1e8,scale/1e8,structure/1e8,0],measure=['absolute','relative','relative','total'],connector={'line':{'color':'#aab8c2'}}))
    fig.update_layout(title='自华进口金额的恒等分解（亿美元）')
    chart(fig)
    st.caption('Δ自华金额 = 基期中国份额×Δ美国总额 + 报告期美国总额×Δ中国份额。分解项精确加总，但属于会计分解，不能当成政策或需求的因果归因。')
    totals=pd.DataFrame({'中国':raw.loc[new,'5700'].sum(),'其他来源':raw.loc[new].sum().sum()-raw.loc[new,'5700'].sum()},index=['报告期'])
    totals.loc['基期']=[raw.loc[old,'5700'].sum(),raw.loc[old].sum().sum()-raw.loc[old,'5700'].sum()]
    chart(px.bar(totals.div(1e8).reset_index().melt(id_vars='index',var_name='来源',value_name='亿美元'),x='index',y='亿美元',color='来源',barmode='group',title='中国与其他来源的金额变化',labels={'index':'期间'}))
    table=pd.DataFrame({'分解项':['基期自华金额','美国总进口规模项','中国份额变化项','报告期自华金额'], '金额（美元）':[row['基期金额'],scale,structure,row['报告期金额']]})
    downloadable(table,'china_decomposition')


def diversification(shares,raw,names,start,end,topn):
    st.divider();st.subheader('多元化深度：来源数量多，是否也意味着份额分散？')
    c=concentration(shares.loc[start:end])
    chart(px.line(c.reset_index(),x='time',y=['有效来源数（1/HHI）','熵有效来源数'],title='按份额分布折算的有效来源数'))
    st.caption('1/HHI更强调大来源地；熵有效来源数对较小来源地更敏感。两者均不直接等同供应链安全或风险。')
    leaders=raw.loc[start:end].sum().nlargest(topn).index
    heat=shares.loc[start:end,leaders].rename(columns={c:label_country(c,names) for c in leaders}).T*100
    chart(px.imshow(heat,aspect='auto',color_continuous_scale='Blues',labels={'color':'份额（%）'},title='主要来源地份额热力图（原始当月口径）'))
    ordered=shares.loc[end].sort_values(ascending=False)
    coverage=pd.DataFrame({'来源地数量':range(1,len(ordered)+1),'累计份额（%）':ordered.cumsum().values*100})
    chart(px.line(coverage,x='来源地数量',y='累计份额（%）',title=f'{end}主要来源地累计覆盖率'))
    n80=int((ordered.cumsum()<.8).sum()+1);n90=int((ordered.cumsum()<.9).sum()+1)
    st.info(f'{end}当月，前 {n80} 个来源地覆盖至少80%进口，前 {n90} 个来源地覆盖至少90%。')
    result=compare_control(raw,end,'diversity_comparison')
    if result is not None:
        changes,_,_=result
        distance=float(changes['份额变化（百分点）'].abs().sum()/2)
        st.metric('来源份额重分配幅度',f'{distance:.2f} 个百分点')
        st.caption('各来源地份额绝对变化之和的一半，衡量两个区间的结构距离；不是实际转单金额。')
    downloadable(c.reset_index(),'diversification_deep')


def geographic(df,geo,raw,names,start,end,topn,key):
    st.divider();st.subheader('地区下钻：全国分布背后的来源结构')
    state_names=json.loads((ROOT/'state_names.json').read_text(encoding='utf-8'))
    if geo=='STATE':geo_names={g:g+' · '+state_names.get(g,g) for g in df[geo].unique()}
    else:
        mapping=df.dropna(subset=['PORT_NAME']).drop_duplicates('PORT',keep='last').set_index('PORT').PORT_NAME
        geo_names={g:g+' · '+str(mapping.get(g,'名称待核')) for g in df[geo].unique()}
    f=df[df.time.between(start,end)]
    ranking=f.groupby(geo).GEN_VAL_MO.sum().sort_values(ascending=False)
    ranking=ranking[ranking.gt(0)]
    local_china=f[f.CTY_CODE=='5700'].groupby(geo).GEN_VAL_MO.sum()
    ch_distribution=local_china.reindex(ranking.index,fill_value=0)
    if ch_distribution.sum()>0:
        all_share=ranking/ranking.sum()
        china_share=ch_distribution/ch_distribution.sum()
        distance=(china_share-all_share).abs().sum()/2*100
        a,b,c=st.columns(3)
        a.metric('全部来源：前三地区占比',f'{all_share.nlargest(3).sum():.1%}')
        b.metric('中国来源：前三地区占比',f'{china_share.nlargest(3).sum():.1%}')
        c.metric('中国与整体空间分布差异',f'{distance:.1f} 个百分点')
        st.caption('前三地区分别按各自分布排序。空间差异＝两组地区份额绝对差之和的一半；为0时分布一致，越大表示中国来源的空间分布越不同于整体，不代表贸易风险。')
    scatter=ranking.rename('当地进口额（美元）').to_frame()
    scatter['自华进口额（美元）']=local_china.reindex(scatter.index,fill_value=0)
    scatter['中国占当地进口比重（%）']=scatter['自华进口额（美元）']/scatter['当地进口额（美元）']*100
    scatter['地区']=scatter.index.map(geo_names)
    threshold=st.number_input('规模与中国份额图：最低当地进口额（美元）',min_value=0,value=1000000,step=1000000,key=key+'_scatter_min')
    plotted=scatter[scatter['当地进口额（美元）']>=threshold]
    if not plotted.empty:
        chart(px.scatter(plotted,x='当地进口额（美元）',y='中国占当地进口比重（%）',size='自华进口额（美元）',hover_name='地区',log_x=True,size_max=50,title='进口规模与中国份额：识别规模大且中国占比高的地区'))
    else:st.info('没有达到当前金额阈值的地区，请降低阈值。')
    st.caption('横轴使用对数刻度，气泡大小为自华金额；可过滤小额地区，避免极小金额的高占比掩盖主要分布。')
    chosen=st.selectbox('选择地区查看详情',ranking.index.tolist(),format_func=lambda g:geo_names[g],key=key+'_drill')
    local=df[df[geo]==chosen].pivot_table(index='time',columns='CTY_CODE',values='GEN_VAL_MO',aggfunc='sum',fill_value=0).reindex(raw.index,fill_value=0)
    totals=local.sum(axis=1)
    ch=local.get('5700',pd.Series(0,index=raw.index))
    trend=pd.DataFrame({'全部来源':totals/1e8,'中国来源':ch/1e8}).loc[start:end]
    left,right=st.columns(2)
    with left:chart(px.line(trend.reset_index().melt(id_vars='time',var_name='来源',value_name='亿美元'),x='time',y='亿美元',color='来源',title='该地区月度进口金额'))
    share=(ch/totals.where(totals.gt(0))*100).loc[start:end]
    with right:chart(px.line(share.rename('中国份额（%）').reset_index(),x='time',y='中国份额（%）',title='该地区进口中的中国份额'))
    amounts=local.loc[start:end].sum().sort_values(ascending=False)
    p=amounts.head(topn).rename('金额').reset_index();p['来源地']=p.CTY_CODE.map(lambda c:label_country(c,names))
    chart(px.bar(p.iloc[::-1],x='金额',y='来源地',orientation='h',title='该地区主要来源地'))
    leaders=raw.loc[start:end].sum().nlargest(topn).index
    cross=f[f[geo].isin(ranking.head(8).index)].pivot_table(index='CTY_CODE',columns=geo,values='GEN_VAL_MO',aggfunc='sum',fill_value=0)
    cross=cross.div(cross.sum(axis=0).where(cross.sum(axis=0).gt(0)),axis=1)*100
    cross=cross.reindex(leaders,fill_value=0).rename(index={c:label_country(c,names) for c in leaders})
    chart(px.imshow(cross,aspect='auto',color_continuous_scale='Blues',labels={'color':'当地份额（%）'},title='主要来源地 × 主要地区：每列以当地全部进口为分母'))
    monthly=f.pivot_table(index='time',columns=geo,values='GEN_VAL_MO',aggfunc='sum',fill_value=0).reindex(raw.loc[start:end].index,fill_value=0)
    trend=monthly[ranking.head(6).index].div(1e8)
    chart(px.line(trend.reset_index().melt(id_vars='time',var_name='地区代码',value_name='亿美元'),x='time',y='亿美元',color='地区代码',title='主要地区月度趋势（固定所选区间前六名）'))
    result=compare_control(raw,end,key+'_compare')
    if result is not None:
        _,old,new=result
        part=df[df.time.isin(old+new)].copy();part['阶段']=np.where(part.time.isin(new),'报告期','基期')
        change=part.pivot_table(index=geo,columns='阶段',values='GEN_VAL_MO',aggfunc='sum',fill_value=0).reindex(columns=['基期','报告期'],fill_value=0)
        change['变化（亿美元）']=(change['报告期']-change['基期'])/1e8
        big=change.loc[change['变化（亿美元）'].abs().nlargest(12).index].reset_index().sort_values('变化（亿美元）')
        big['地区']=big[geo].map(geo_names)
        chart(px.bar(big,x='变化（亿美元）',y='地区',orientation='h',title='哪些地区的进口金额变化最大？'))
        downloadable(change.reset_index(),key+'_change_table')
    if geo=='PORT':
        st.markdown('**运输观察：海运与空运的毛重构成**')
        country=st.selectbox('运输分析来源',['全部来源']+list(raw.columns),format_func=lambda c:label_country(c,names) if c!='全部来源' else c,key='transport_country')
        transport=f if country=='全部来源' else f[f.CTY_CODE==country]
        weight=transport.groupby('time')[['VES_WGT_MO','AIR_WGT_MO']].sum().reindex(raw.loc[start:end].index,fill_value=0)
        weight.columns=['海运毛重','空运毛重']
        pct=weight.div(weight.sum(axis=1).where(weight.sum(axis=1).gt(0)),axis=0)*100
        chart(px.area(pct.reset_index().melt(id_vars='time',var_name='运输方式',value_name='海空合计内占比（%）'),x='time',y='海空合计内占比（%）',color='运输方式',title='海空毛重结构'))
        chart(px.line(weight.div(1e6).reset_index().melt(id_vars='time',var_name='运输方式',value_name='百万千克'),x='time',y='百万千克',color='运输方式',title='海空毛重规模'))
        st.caption('分母仅为海运加空运毛重，含包装，不包括陆路重量；不用于推断件数、单价或电池用途。全国重量仅从口岸表汇总一次。')
        downloadable(weight.reset_index(),'transport_raw')
    downloadable(pd.DataFrame({'月份':local.loc[start:end].index,'全部进口额':totals.loc[start:end].values,'自华进口额':ch.loc[start:end].values,'中国份额（%）':share.values}),key+'_local_trend')


def quality(state,port):
    st.subheader('可核查的数据质量')
    summary,differences=quality_summary(state,port)
    st.dataframe(summary,hide_index=True,width='stretch')
    st.metric('国家×月份金额不一致的组合数',str(differences))
    st.markdown('''| 新增指标 | 解释 |
| --- | --- |
| 对美国进口增长贡献 | 某来源地金额变化÷基期美国进口总额，单位百分点 |
| 有效来源数 | 1/HHI；熵有效来源数为exp(−Σs·ln s) |
| 结构重分配幅度 | 0.5×Σ份额绝对变化，单位百分点 |
| 等长比较 | 以所选末月为终点，最近k个月与紧邻此前k个月比较 |
''')
    st.caption('新增分析均为描述性统计。未将金额/毛重比值解释为单价，不将份额增减解释为政策或供应替代的因果证据。')
