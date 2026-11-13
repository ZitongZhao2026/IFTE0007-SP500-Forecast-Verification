# IFTE0007 最终预测执行记录（2026-11-13）

信息截止：2026-11-13 12:00 GMT。目标：2026-11-20 S&P 500 Price Index 官方收盘点位；目标日仅有 `PLANNED_OPEN` 证据，实际会话和实际收盘尚未发生。

最终获批的单次重试使用七因子 Ridge（α=1），逐次训练内 StandardScaler、Expanding Window、修正后的历史 Proxy PIT 标签。Live P0 为 Yahoo `^GSPC` 2026-11-12 Close **7,592.40**；预测累计简单收益率 **−0.005260040020305717**（−0.526004%），预测点位 **7,552.463672149831**（报告展示为 **7,552.46**）。训练样本 **869** 条。Live 输入状态 `LIVE_INPUTS_CUTOFF_VERIFIED`，历史训练 `PROXY_HISTORICAL_INPUTS`，Strict PIT `STRICT_PIT_UNKNOWN`，正式评分 `NOT_AUTHORIZED`。

冻结训练 manifest SHA-256：`5ac4fcd831041a851ac2038e12ddef4b2391245a5e41cebc53b9847ead336a27`；冻结 Live bundle SHA-256：`17f0da91ccf4f925b5a5f30dc681d51f99cd73bd23fb15e6c2342d0b5ddd826a`。用户明确批准只对这一对哈希单次重试。预测 JSON SHA-256：`ab11509624c4923e924fb624a305cddaa66a2262728e6c99252110d49b0c627b`；执行 manifest SHA-256：`5661f6cab50bb3198bacad9e3df1ec75d3c233a5c0583a705f8b2f1471698997`。

先前 v8 单次尝试在内存拟合后因隔离目录缺少 `model_candidates.json` 而失败，未写预测文件。其两份部分产物保留。v10 在拟合前绑定原样复制的模型配置，并用 `.consumed.json` 一次性标记批准。两个尝试、两份批准和两组哈希均有独立记录，旧批准未用于重试。

独立只读复核：**PASS**。复核确认 v10 的17份训练冻结文件、执行 manifest 的46份文件哈希一致；869条训练标签按代理规则已成熟；P0、七因子、收益率到点位的换算一致；最终 JSON 不含目标实际价；首次失败产物未被改写。Treasury首次发布时间及精确会话结束时刻仍UNKNOWN，11月12日 Yahoo价格没有截止前同日FRED记录，11月20日实际会话未发生。通过本次来源/截止门控不等于 Strict PIT 认证。

这次执行仅生成预测，不读取或填入2026-11-20实际收盘，不计算正式课程分数。
