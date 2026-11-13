# 首次单次运行失败记录（保留原状）

- 绑定批准：`single_run_approval_v8.json`，训练 manifest SHA-256 `8584a58a1597c9a3398e32cd09a0777442444d68e14379dae7dea482bef24ce4`，Live bundle SHA-256 `17f0da91ccf4f925b5a5f30dc681d51f99cd73bd23fb15e6c2342d0b5ddd826a`。
- 运行入口：隔离的 `run_forecast_bound.py`；输入门控已过。模型拟合及内存中点位换算之后，执行 manifest 构建因同目录缺少 `model_candidates.json` 抛出 `FileNotFoundError`。
- 已写出部分产物：`final_forecast_2026-11-20_training_membership.csv` 和 `final_forecast_2026-11-20_live_input_snapshot.json`。**没有**最终预测 JSON 或 execution manifest；未发布预测点位。
- 原设计配置 `model_candidates.json` 已原样复制到隔离目录，原件/副本 SHA-256 均为 `404730110516cfde4d1ba2898d843d7559cc48d83ff0a718c79e3bf2f5508e06`。旧部分产物保留，不覆盖。
- 首次批准按一次使用处理，不能复用。隔离门控已增补拟合前文件绑定与一次性使用标记；新训练 manifest v10 需新的双哈希单次运行批准。
- 独立只读复核确认了失败点、部分产物和未生成最终预测文件。
