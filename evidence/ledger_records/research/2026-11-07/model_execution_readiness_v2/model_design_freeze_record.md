# IFTE0007 模型设计批准记录（仅模型设计）

状态：`MODEL_DESIGN_APPROVED`（2026-11-07T22:30:46Z）。用户/项目统筹者已明确批准主模型设计。本批准不构成数据快照批准、正式数据冻结或运行授权。审批事件：`MODEL_DESIGN_APPROVAL_2026-11-07T223046Z`。

## 建议候选

- 主模型：`SEVEN_FACTOR_RIDGE`，`alpha=1.0`，特征顺序 `RET5, RET20, RV20, VIX, UST10Y, UST3M, SPREAD`，其中 `SPREAD = UST10Y - UST2Y`。
- 备选：`VIX_UST10Y_RIDGE`，`alpha=1.0`，特征 `VIX, UST10Y`。
- 两者均为 `StandardScaler → Ridge`；Scaler 与 Ridge 只在本次实际合格的 expanding 训练行中 fit。训练目标为修正协议下从 P0 到下一周五（按批准回退规则处理休市）的累计简单收益率；点位为 `P0 × (1 + predicted_return)`。
- 训练方式、P0、目标、Corrected Proxy PIT 规则、标签成熟门控和因子公式均沿用已批准定义；本记录不授权修改任何定义。

## 选模证据及限制

主要依据为 `research/2026-11-06/corrected_exploratory_comparison/metrics.csv` 与 `research_report.md`：

| 期间 | 七因子 Ridge MAPE | VIX+UST10Y Ridge MAPE | 同口径观察 |
|---|---:|---:|---|
| G3 开发期，257个共同起点 | 2.0941% | 2.0704% | 双因子低0.0237个百分点 |
| G4，156个共同起点 | 1.5537% | 1.6409% | 七因子低0.0872个百分点 |

G3结果已经多次查看并参与开发决策；G4明确为 `Previously Exposed / Non-independent`。两段方向并不一致，不证明任一模型未来优越。G4不是独立Holdout。Strict PIT仍为 `UNKNOWN`。用户指定七因子为主候选、双因子为备选；这记录的是待审阅建议，不宣称七因子在全部历史表现上领先。旧版 G3-C Round 5 仅留作历史探索记录，不作为本次主要选模依据。

## 执行与数据快照分离

模型设计审批与某次具体运行批准必须分别登记。任何正式运行授权须绑定：所选 model ID、cutoff/目标、Corrected Proxy rules SHA-256、完整训练快照 SHA-256、实时输入/证据包 SHA-256、代码版本及批准记录。备选模型不得自动启用；七因子门控失败时停止。只有人工对备选配置和其专属数据资格作出独立明确批准，才可另行运行。

## 人工审批区（未填写）

| 项目 | 状态 |
|---|---|
| 主模型设计批准 | `APPROVED`（用户本会话明确决定；未提供姓名或签名） |
| 备选模型设计批准 | `NOT APPROVED`（保留候选；不得自动启用） |
| 本次预测运行批准 | `NOT_APPROVED` |
| 最终数据快照 | `BLOCKED`；数据与证据哈希尚未核准 |
| Strict PIT | `STRICT_PIT_UNKNOWN` |

批准人、批准时间、决定引用、目标运行及绑定哈希均留空，需由 Common Data Coordinator/用户本人填写；本 Agent 不代签。


## 本次审批登记

批准人记录为“User / project coordinator”（依据本会话明确指令；未提供个人姓名或签名）。批准范围仅为：七因子 Ridge alpha=1及上述七因子、Expanding Window、训练窗口内 StandardScaler、Corrected Exploratory Proxy PIT研究约定。双因子仅为未获批准的备选，不得自动回退。记录时间为 `2026-11-07T22:30:46Z`。数据快照状态仍 `BLOCKED`；本次预测执行仍 `NOT_APPROVED`；Strict PIT仍 `UNKNOWN`。
