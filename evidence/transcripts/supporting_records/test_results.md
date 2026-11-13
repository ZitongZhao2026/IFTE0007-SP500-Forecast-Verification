# 门控测试记录

在现有 `/opt/anaconda3/bin/python` 环境执行 `python -m unittest -v test_run_comparison test_precheck test_execution_gate`，14项通过。

- 合成输入：历史特征代理时间晚于cutoff、未成熟标签、已知价格冲突、错误目标会话、错误P0及伦敦时区cutoff、非有限值、收益标签不一致均被拒绝或排除。
- 按特征区分训练资格的测试保留不依赖VIX的单因子样本；有VIX的七因子池拒绝该不合格VIX记录。
- 冻结配置遭修改时，执行路径在拟合前拒绝；模拟训练失败时，执行路径保存失败原因且不输出预测和指标。执行路径测试使用临时合成记录与mock，不拟合真实或合成模型。
- `frozen_admission.csv` 和 `frozen_training_membership.csv` 在误差计算前生成并绑定配置哈希，真实预测执行前重新核验。输入时间与价格检查仅证明按照代理规则一致，不证明外部数据首次可得时间或实际会话完整性。
