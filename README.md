# 美国锂离子蓄电池进口观察

标准Python/Streamlit项目。全部图表使用用户提供的真实Census数据快照，不使用模拟贸易数据。包含2017-01至2026-08的初始数据，解压即可运行，不需要密钥查看初始看板。

## 已有线上应用如何升级

本次为研究分析扩展版。无需删除仓库或重新创建应用。

必须更新四个文件（上传到仓库根目录）：

1. 覆盖 app.py。
2. 覆盖 model.py。
3. 新增 research.py。
4. 新增 state_names.json。

可选同步README.md、test_dashboard.py、验证结果.txt和本说明；data、密钥、Actions配置均可沿用已有版本。不要将ZIP直接传入仓库，不要多套一层目录。提交后等待Streamlit同步，必要时Reboot app。上述四个文件必须同一次提交，避免app.py先更新而research.py尚未存在。

来源地中文显示已覆盖当前数据全部114个统计代码；使用中国台湾、中国香港、中国澳门。美国州和卸货口岸保留英文，底层API代码与数据不改动。

地理指标增加中国份额相对全国倍数、全部与中国来源的前三地区占比，以及两者空间分布差异。

新增分析按研究问题组织：规模与周期；金额与份额是否同向；自华进口变化分解；实际来源数与有效来源数；地区规模与中国份额；地区来源结构、月度走势及金额增减贡献；海空毛重观察。所有比较以完整的等长不重叠区间计算，不将描述性结果解释为政策因果关系。

新增研究图表主要使用原始当月金额，标题或说明明确标注；侧栏滚动口径仍仅作用于原有全国趋势和顶部指标，地理与期间比较始终使用原始金额。

## 第一步：先本地查看

推荐Python 3.12。终端进入本目录：

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows也可在安装依赖后双击start_windows.bat。浏览器通常打开localhost:8501。这一步只用于检查项目；所有人共享需要完成下面的云端部署。

## 第二步：上传GitHub

1. 新建仓库，例如us-battery-imports。公开仓库的代码和数据可被任何人读取；私有仓库按团队实际需要配置访问。
2. 将本目录内部所有文件上传至仓库根目录，不要仅上传ZIP。app.py应位于根目录。
3. 必须包含.github/workflows/update.yml、.streamlit/config.toml以及整个data目录。操作系统隐藏点目录时，用显示隐藏文件或Git上传方式确认它们存在。
4. 分支使用默认分支，例如main。部署选同一个分支。

本项目没有代建仓库或上传数据到GitHub。

## 第三步：配置云端API更新

GitHub仓库 → Settings → Secrets and variables → Actions → New repository secret：

- Name：CENSUS_API_KEY
- Secret：你自己的Census密钥

密钥不要写在代码、公开文件、聊天或README中。官方申请入口：https://api.census.gov/data/key_signup.html

仓库Actions页手动运行“Update Census imports”。如平台或组织禁用Actions，先由仓库管理员启用；如果分支保护禁止机器人直接写入，需按仓库规则改为PR发布或独立数据分支，不应绕过保护。

工作流默认每天UTC02:23检查，即北京时间10:23；每年1、4、7、10月1日执行全量回查，也可手动勾选full。日常回查24个月并检查新月份。定时任务可能延迟；公开仓库长期无活动时GitHub可能停用定时任务，需要定期检查Actions状态，不是严格实时服务。

更新成功后机器人提交data目录；更新失败时保留有效数据，提交status.json使页面可显示失败状态，并将该次工作流标记为失败。默认保留工作目录中当前及上一版快照，Git历史仍有旧数据，长期运行仓库会增长。

## 第四步：部署可分享网站

进入Streamlit Community Cloud：https://share.streamlit.io

创建应用，选择上面的GitHub仓库和默认分支：

- Main file path：app.py
- Python version：3.12
- 安装依赖：由requirements.txt自动处理

部署成功后获得streamlit.app网址。按需要配置应用访问权限，再把这个网址发给老师和同学。Census密钥只在GitHub Actions中使用，Streamlit页面不需要密钥。

更新链路：GitHub Actions下载真实数据 → 校验后提交仓库 → Streamlit云端同步仓库 → 访问者打开或重新读取页面获得新数据。无需你的电脑开机。GitHub提交和云平台同步之间有延迟，不承诺即时刷新。

当前只提供可部署项目，尚未创建GitHub仓库、配置真实密钥或实际上线。云端首次运行必须检查Actions结果和Streamlit日志，确认账号权限、接口可用性及同步均正常。

## 项目文件

| 文件 | 修改内容 |
| --- | --- |
| app.py | 页面、图表、筛选、文字 |
| model.py | 数据读取、来源结构和地理指标 |
| update_data.py | Census采集、校验、整月替换及版本发布 |
| .github/workflows/update.yml | 每日/季度任务 |
| maintenance.py | 快照保留策略 |
| data/current.json | 当前有效数据版本指针 |
| data/status.json | 最近检查状态 |
| data/versions/... | 两表Parquet与版本说明 |

数据使用英文原始字段，time为YYYY-MM；CTY_CODE、STATE、PORT为字符串，口岸前导零保留。初始原始数据保留全零记录，与此前删除零记录的Excel行数不同，但金额相同。口岸名称缺失时显示代码。

## 页面与指标

- 总览：进口额、同比、年度同期比较。
- 来源地结构：期间金额排名、固定Top N份额、基于全部国家的HHI和CR5。
- 中国地位：自华金额、中国份额、来源地份额同比变化。
- 目的地州：州地图、金额排名、当地中国份额、全国自华进口空间占比。
- 卸货口岸：同类指标及明细下载。
- 数据与方法：口径、字段来源和当前数据版本。

“全国趋势口径”只影响全国趋势及顶部指标。期间排名与地理分布始终按所选区间原始当月金额求和；年度比较明确标注独立于区间筛选，并默认所有年份都比较1月至最新已发布月份。

金额为一般进口海关价值，不是CIF；州不代表最终消费地；卸货口岸不等同报关口岸。两表不能相加，也不能连接成真实口岸到州的路线。没有件数或电池单价推断，不将份额变化解释成政策因果关系。

地图需要浏览器能够加载Plotly地理资源，受限网络可能无法显示底图；排名和数据表不依赖地图。

## 更新逻辑

如果没有本地版本，首次从2017年起下载。已有版本时重新下载最近24个月及后续候选月份。每月两接口成功且校验后，整月替换旧数据，不直接追加。整批成功后最后切换current.json，防止两表版本不一致。

仅将两接口都返回HTTP204的新尾部月份视为尚无数据；其他错误保留旧版并记录失败。单端发布不同步、历史月份消失、明细与全国总额不等、国家月度金额不同、重复键等均阻止发布。按月查询；如果单月响应仍接近行数上限则停止，需要进一步拆分请求。

本地手动API更新：

```powershell
$env:CENSUS_API_KEY="自己的密钥"
python update_data.py --lookback 24
```

全量：python update_data.py --full。并发锁异常残留时，先确认更新程序已经停止，再删除data/update.lock。

## 验证

```powershell
python test_update.py
python test_dashboard.py
```

附件初始化已核对两表116个月金额及国家月度金额一致。真实API联网、GitHub提交和云平台部署尚未端到端验证，需要你的账号与密钥完成。初始metadata中的成功时间是附件初始化时间，不是官方最新发布或实时API检查时间。

官方文档：
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://api.census.gov/data/timeseries/intltrade/imports/statehs/variables.html
- https://api.census.gov/data/timeseries/intltrade/imports/porths/variables.html
