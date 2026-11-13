# Transcript evidence index

The original Codex rollout is an active append-only local file. Its SHA-256 below identifies the bytes captured for extraction, not a claim that the file will never append.

Session source `$CODEX_HOME/sessions/2026/10/28/rollout-2026-10-28T14-42-24-01a182f6-577e-73f1-81fc-8f80b8b3ccc6.jsonl`; captured SHA-256 `defd505e09c8502ef5d2ab21ff7d3c122516ef75016db1dc47592caf80c85966`. Exported session fields are **partial**, exact selections by JSONL line, not a byte-identical copy of the rollout.

| JSONL line | UTC timestamp | Type | In short extract |
|---:|---|---|---|
| 16 | 2026-10-28T14:42:27.035Z | message / user | yes |
| 2590 | 2026-10-28T19:24:04.899Z | message / user | yes |
| 2761 | 2026-10-28T19:31:41.067Z | message / user | yes |
| 3200 | 2026-10-28T19:48:15.005Z | custom_tool_call / exec | yes |
| 3205 | 2026-10-28T19:48:15.146Z | custom_tool_call_output / tool_output | yes |
| 20593 | 2026-11-05T10:10:13.772Z | message / user | yes |
| 23899 | 2026-11-06T01:27:48.871Z | message / assistant | yes |
| 24511 | 2026-11-06T01:51:49.696Z | custom_tool_call / exec | yes |
| 24526 | 2026-11-06T01:52:04.481Z | custom_tool_call_output / tool_output | yes |
| 28975 | 2026-11-07T22:30:34.930Z | message / user | yes |
| 29060 | 2026-11-07T22:33:45.826Z | message / assistant | indexed only |

## Complete copied project records

Every file below is an unmodified byte-identical copy in the separate local archive. The selected seven supporting records are also copied byte-identically into Eva's ZIP. A folder date is a locator, not proof of file creation or retrieval time.

| Original location | Documented date and limit | Original SHA-256 | Archive copy SHA-256 | Evidence type |
|---|---|---|---|---|
| `$PROJECT_ROOT/governance/approval_log.jsonl` | per-event dates in JSONL; no single file creation time established | `18ff5204a4b8ebe427267d83ef6ea72eac0335f5d4f2b8016e6dd1e9c62d5ae7` | `18ff5204a4b8ebe427267d83ef6ea72eac0335f5d4f2b8016e6dd1e9c62d5ae7` | approval |
| `$PROJECT_ROOT/research/2026-10-28/g1_vix_treasury/quality_researcher.md` | 2026-10-28 (directory date only; exact record time UNKNOWN) | `e96fd4072280a378b6b0cd3a595400f57578ffe7e8949d789f33b76fc5c8f037` | `e96fd4072280a378b6b0cd3a595400f57578ffe7e8949d789f33b76fc5c8f037` | research record |
| `$PROJECT_ROOT/research/2026-10-29/g2_price_rolling/independent_audit.md` | 2026-10-29 (directory date only; exact record time UNKNOWN) | `54972012a618eb0cbf3d90be1768db4166e3cc4cf2b3745429d4739b64d3b421` | `54972012a618eb0cbf3d90be1768db4166e3cc4cf2b3745429d4739b64d3b421` | audit |
| `$PROJECT_ROOT/research/2026-10-29/g2_price_rolling/negative_test_result.json` | 2026-10-29 (directory date only; exact record time UNKNOWN) | `c68cee4dd094ede75d8175a383e4b06d342f04df156ca3a414d07346efc35323` | `c68cee4dd094ede75d8175a383e4b06d342f04df156ca3a414d07346efc35323` | research record |
| `$PROJECT_ROOT/research/2026-11-06/corrected_exploratory_comparison/rules.json` | 2026-11-06 (directory date only; exact record time UNKNOWN) | `9f664e2e82b7510bc98a10ea1bbf31c83c1ded968869a0fbe45c4fba0cd7a46a` | `9f664e2e82b7510bc98a10ea1bbf31c83c1ded968869a0fbe45c4fba0cd7a46a` | research record |
| `$PROJECT_ROOT/research/2026-11-06/corrected_exploratory_comparison/test_results.md` | 2026-11-06 (directory date only; exact record time UNKNOWN) | `d75e3aae16fcbe830fbfbfc0de1cd55cbb8c450c9d4e6b0282a2f084366eaa27` | `d75e3aae16fcbe830fbfbfc0de1cd55cbb8c450c9d4e6b0282a2f084366eaa27` | audit |
| `$PROJECT_ROOT/research/2026-11-06/corrected_exploratory_comparison/independent_review.md` | 2026-11-06 (directory date only; exact record time UNKNOWN) | `1bde717368c68bf691ce0512cdbb9ab320e3100e897eed0313269e9b45307d6d` | `1bde717368c68bf691ce0512cdbb9ab320e3100e897eed0313269e9b45307d6d` | audit |
| `$PROJECT_ROOT/research/2026-11-06/corrected_exploratory_comparison/research_report.md` | 2026-11-06 (directory date only; exact record time UNKNOWN) | `02a5be190f6c14cd07442ec8c47370af663c1ccc3f85d6d6fbf10f4588f72edc` | `02a5be190f6c14cd07442ec8c47370af663c1ccc3f85d6d6fbf10f4588f72edc` | research record |
| `$PROJECT_ROOT/research/2026-11-07/model_execution_readiness_v2/model_design_approval_events.jsonl` | approval event 2026-11-07T22:30:46Z; file creation time not independently established | `084c46469214304b5bf5999a18b5470896b86c22891ad77884df272fe5f9967c` | `084c46469214304b5bf5999a18b5470896b86c22891ad77884df272fe5f9967c` | approval |
| `$PROJECT_ROOT/research/2026-11-07/model_execution_readiness_v2/model_design_approval_record.json` | approval event 2026-11-07T22:30:46Z; file creation time not independently established | `219b5e8b75da465eec312feebfb948228821bbc7d3a1e09dc528617307456ec4` | `219b5e8b75da465eec312feebfb948228821bbc7d3a1e09dc528617307456ec4` | approval |
| `$PROJECT_ROOT/research/2026-11-07/model_execution_readiness_v2/independent_read_only_review.md` | 2026-11-07 (directory date only; exact record time UNKNOWN) | `5b762636311655231f25ea1e827a4df3421abc573a03d03be99eafb5b3379b11` | `5b762636311655231f25ea1e827a4df3421abc573a03d03be99eafb5b3379b11` | audit |
| `$PROJECT_ROOT/research/2026-11-10/eva_v2_empirical_completion/completion_report.md` | 2026-11-10 (directory date only; exact record time UNKNOWN) | `258d054e1ee129fb54a1c3b2797bf6483b88f66173b3b5f79ad9518a9aaa60c2` | `258d054e1ee129fb54a1c3b2797bf6483b88f66173b3b5f79ad9518a9aaa60c2` | research record |

Report context PDF located at `$PROJECT_ROOT/research/2026-11-10/eva_v2_empirical_handover/07_methods_and_source_lineage/report_context/IFTE0007_Group_Review_Draft_v2（eva1.0）.pdf`; SHA-256 `38cd3d14cf94ac4e63e1e81245f0774907f881e97f2242676327534c20fbdc5c`. It was read to check Section 4 / Figure 1 / Table A7 wording but is **not** included in this package.

All selected session excerpts are partial. The raw source, not the exported excerpt, is the original transcript. See `REDACTION_LOG.csv` and `NOT_FOUND.md`.
