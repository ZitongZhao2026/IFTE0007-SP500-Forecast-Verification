# G1 VIX 与 Treasury 原文件质量核查 — Data Researcher

协议 0.1.4-draft，SHA-256 `b80853fb0fa9135d58cf4e3d0c308bc11e354db6ade78b90dadf51814f71b706`；P03/P04。任务为文件描述与质量核查，未构建因子；代码 `quality_check_researcher.py`；机器可读核查结果 `quality_researcher_evidence.json`；日期差异 `quality_date_differences.csv`。所有输入哈希在代码读取前后核对一致。

## 用户提供的原始 CSV 快照

来源为用户按上一轮请求手动下载并置于 raw 目录；请求入口分别为 [Cboe VIX](https://www.cboe.com/tradable_products/vix/vix_historical_data)、[Treasury historical archive](https://home.treasury.gov/interest-rates-data-csv-archive/) 和 [Treasury daily rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve)。这些入口是所请求的来源，并非对具体文件下载 URL、响应或来源真实性的独立证明；具体 URL、实际下载时间和版本均 UNKNOWN。文件系统时间不等于下载时间。

| 原始文件 | SHA-256 | 行数 | 最早—最晚日期 | 日期顺序 |
|---|---|---:|---|---|
| raw/VIX_History.csv | `6da7f149324ec456c80f6d7e96c90b5d3bcaa3d0f6a4274f7840542db9809265` | 9303 | 1990-01-02—2026-10-27 | 升序 |
| raw/yield-curve-rates-1990-2024.csv | `258a594eb64e9d21d9e8574b0b8580b0a5230dce56bb284ec6aa49a9a260897f` | 8757 | 1990-01-02—2024-12-31 | 降序 |
| raw/daily-treasury-rates-2025.csv | `cf2fa3da7f160384b63d2ead698532b1d76cd9f789ce4911e2304db85b14e6d5` | 249 | 2025-01-02—2025-12-31 | 降序 |
| raw/daily-treasury-rates-2026.csv | `7eb8494d3f36efef53017dcb1c22548fdabaca3a1aac8a25424eef13d693398d` | 206 | 2026-01-02—2026-10-27 | 降序 |

VIX 表头 `DATE,OPEN,HIGH,LOW,CLOSE`，五列各 0 空值。三个 Treasury CSV 均有 `Date`、`10 Yr`，字段名称相同；历史文件没有 `1.5 Month`，新文件有之，但与 10 Yr 字段不同。历史文件的 10 Yr 有 1 个空值 **2010-10-11**（该行全部期限均空）；2025、2026 各 0。所有列的空值详见 JSON；2025 的 1.5 Month 有 31 个空值，与目标 10 Yr 区分。四个文件均无日期重复和周末日期。字段内容和标题支持它们对应用户所述的指标；具体导出请求与产品口径映射仍需保留来源记录核验。

异常初筛：VIX CLOSE 检查非数值和小于等于零；OHLC 检查 low ≤ open/close ≤ high。Treasury 10 Yr 非数值及范围 [-5,20] 外值标为检查线索（不是事实上的合法值边界）。目标 2010-01-01—2026-10-27 内无上述数值标记；VIX 文件包含 47 条 OHLC 不等式异常，均在 1992—2006 年、早于目标范围，需保留并不证明官方值错误；完整日期在 JSON。无重复不保证没有缺失日期。

## 日期覆盖、衔接与日历限制

比较基准为现有 `../g1_candidate/candidate_price_research_only.csv`：覆盖 2010-01-04—2026-10-27，共 4230 个唯一价格日期；该集合来自候选价格数据及先前重建日历，非权威完整股票或债券日历。其 SHA-256 载于 JSON。

- VIX 包含全部 4230 个价格日期；同范围多 33 日期。多出日期中包含美股休市日，VIX 与股票交易时段并非自动等同；逐日是否为有效 Cboe 发布日仍 UNKNOWN。
- Treasury 在 4230 个价格日期中有 4200 个日期记录，30 个无行；其中已匹配日期 2010-10-11 的 10 Yr 仍为空，因此实际有值日期至多 4199。Treasury 另有 8 个日期不在价格候选集内。日期清单见 CSV/JSON；这些差异不自动等于错误，需依据 Treasury 自身公布日历/公告逐日核验。
- Treasury 文件相互无日期重叠；文件边界为 2024-12-31→2025-01-02、2025-12-31→2026-01-02；两次跨越元旦，但是否有应发布日遗漏需要财政部权威发布日历确认。近年文件头多 `1.5 Month`，`10 Yr` 标题一致不足以证明跨版本计算方法不变。
- 周末检查 PASS；VIX 独立完整交易日历、Treasury 独立完整发布日历、各节假日及特殊休市分类、真正缺行与缺失率均 UNKNOWN。上述 33/30/8 仅为日期集合差异，不应视为缺失率或任意一市场异常。

## 发布时间、版本和对齐

[Treasury methodology](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology) 说明现行曲线基于约美东 15:30 的报价，通常美东 18:00 前公布、可能延迟；2021-12-06 改变方法。这些一般说明不能确定每条历史值的实际公布及渠道可得时间，也不代表历史版本修订已核验。历史结果中的 `Date`、下载时间、原始发布时间、渠道可得时间与 vintage 不相同。VIX 当日收盘同样不能默认在英国当天 12:00 可得。逐条发布时间、修订、渠道到达、历史版本及 PIT 均 UNKNOWN。

未来按每一序列的实际版本及有证据的 available_at 与目标时间 as-of 关联；应考虑英国 BST/GMT 和美东夏令时、股债不同日历，不可按同日期直接合并或将文件行存在等同可用。当前只是接口准备，未进行对齐或因子计算。保存浏览器下载记录、时间和具体 URL；向 Cboe/Treasury 索取逐值历史发布时间、修订/版本及其发布日历，以解决剩余 UNKNOWN。所有日期和数据版本仍未经严格 PIT 准入。
