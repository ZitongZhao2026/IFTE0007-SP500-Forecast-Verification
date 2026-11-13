# IFTE0007 — 2026-11-07 模型设计与执行准备报告

## 结论

- **模型设计已获用户批准（仅限主模型设计）。** 主模型为七因子 Ridge alpha=1；双因子 Ridge 保留为未获批准的备选，不自动启用。此批准不涵盖任何具体数据快照、正式运行或评分。带时戳的决定及前后哈希见 `model_design_approval_events.jsonl`；未伪造姓名或签名。
- **2026训练数据接口已更新到扩展候选输入。** 输入共869行，868行标记为`PROXY_HISTORICAL_INPUTS`，范围F20100205–F20261023；F20261030明确保留为`BLOCKED_SOURCE_NOT_OFFICIALLY_VERIFIED`，未被纳入训练。
- **隔离真实数据post-hoc训练接口测试通过。** 两个固定Pipeline分别对同一868行拟合`StandardScaler → Ridge(alpha=1)`，Scaler均看到868行；没有调用`predict`、保存拟合模型或生成预测。该操作是接口/数值拟合烟测，不是某一历史截止时点合格预测，不是正式训练或最终运行。
- **正式v2训练快照仍BLOCKED。** 新的`prepare_v2_snapshot.py`在最新成熟起点门控停止：拟合截止2026-11-13 12:00Z时预期最新成熟起点F20261030，当前最新准入仅F20261023。它只生成阻断报告，没有生成训练CSV或正式训练manifest。
- Strict PIT、完整实际会话认证、历史真实首次可得时间仍为`UNKNOWN`；正式运行授权`NOT_GRANTED`。

## 选模依据

采用2026-11-06 `corrected_exploratory_comparison`作为本次主要研究依据。G3七因子/双因子MAPE分别为2.0941%/2.0704%；G4分别为1.5537%/1.6409%。G3的双因子较低，G4七因子较低；G4已被查看，`Previously Exposed / Non-independent`。两段结果方向不一致。根据用户指定顺序，七因子列为主候选、双因子列为备选，但没有声称七因子在全部历史评价上更准确。旧G3-C Round 5只保留为历史探索记录，不用作主要选模依据。

## 测试

- 合成门控与接口测试：14/14 PASS；覆盖DST转换、无时区拒绝、标签按target date重算、虚假早成熟拒绝、成熟边界、Y公式、代理时间篡改、未登记Blocked行、F20261030阻断stub、Blocked行带Y、P0同日拒绝及未知特征等。
- 原v2既有合成测试：14/14 PASS。合计28/28 PASS，环境为Python 3.14.6、scikit-learn 1.9.0。
- 真实候选fit-only：PASS，868行；未预测。
- 正式快照准入：BLOCKED（按设计）。接口阻断点：`LATEST_MATURED_ORIGIN_GATE`，原因是缺少已准入的F20261030标签。
- 独立审计先报告过接口门控FAIL；已按其意见修复并保留原异议与修订轨迹，最终复审见`independent_read_only_review.md`。

## 11月13日仍需完成

1. 对F20261030目标2026-11-06，取得并审核获准的官方/授权S&P 500 Price Index结构化收盘记录，生成带完整价格来源、版本、日期和哈希的Y；代理成熟条件已通过，但来源准入仍BLOCKED。Yahoo临时值不能单独解除。
2. 依修正规则重建完整训练候选，最新成熟起点应为F20261030。F20261106的目标为11月13日收盘，晚于12:00Z cutoff，不可纳入。
3. 更新截止前的SPX连续价格窗口、VIX、Treasury 10Y/3M/2Y，保留逐值来源、观察日、可得证据、版本、取数时间和SHA-256；核实目标会话。代理时钟不能升级成真实发布时间证明。
4. 模型设计批准已登记；仍须对准确的训练快照及live evidence hashes作单次运行批准。备选不自动启用，须另行明确批准。
5. 仅在上述条件通过后按`final_execution_runbook.md`执行并归档；任何门控失败即停止。

## 文件及记录位置

接口代码：`training_interface_v3.py`、`prepare_v2_snapshot.py`；post-hoc证据：`posthoc_real_candidate_fit_after_gate_fix_v2/`；准入阻断：`v2_snapshot_preflight_after_gate_fix/`；原始首轮独立异议和修订过程：`execution_attempts.md`、`preliminary_runs_notice.md`。SHA-256见`sha256_manifest.csv`及其sidecar。
