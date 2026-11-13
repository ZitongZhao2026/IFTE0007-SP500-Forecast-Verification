# Independent public release audit

Task: IFTE0007-PUBLIC-EVIDENCE-RELEASE-20261113. Role: independent Leakage Auditor. Review time: 2026-11-13T16:49:17.117977+00:00. Scope: the new filtered public evidence release only. No historical backtest, forecast execution, coefficient reconstruction or repeat search of the archived records was performed.

Protocol: `0.1.4-draft`; SHA-256 `b80853fb0fa9135d58cf4e3d0c308bc11e354db6ade78b90dadf51814f71b706`, matched to the recorded human approval. Basis: P03 source/publication distinctions; P08 authentic evidence and sharing; P10 independent review and bounded authorization. Current authorization permits filtered publication; it does not permit new modelling.

## Frozen inputs

- Reviewed public candidate: 125 files before adding this audit and refreshing its inventory.
- Candidate ZIP SHA-256: `95a2a5b70df74a8c09aa1872cc24b6da184ab9e620c5d8e6527cb90caf8609a9`.
- Sorted relative-file/SHA-256 inventory digest: `28420eb976724de18046e2a09912a545826d04857a9ac13bcc939ba2d428ae61`.
- Existing repository tree: `db1fbf6b07a9aefd512cacc03e996764e23cc98e`.
- Repaired source ZIP identity: `db54e7befb8dfa6c7f7699f488df98f3dc31fb7e254b38909bbcd6c2fb4fac4d`.
- Manifest: all 149 repaired source members accounted for; 34 explicitly excluded. Three provider metadata projections additionally identify their original hashes and transformations.

## Checks

| Check | Result |
|---|---|
| All public files screened for credential patterns, email addresses, personal identifiers and machine-specific absolute paths | PASS: no findings in reviewed bytes |
| Source classification and tabular headers reviewed for raw/row-level financial inputs, per-origin financial export files and private execution records | PASS within declared scope: uncertain files excluded; retained tables are aggregates, dates/eligibility/membership metadata or explicitly described scalar sensitivity arithmetic |
| Four additional historical case-detail documents flagged during independent review | Resolved: excluded whole, unchanged originals retained outside public release; exclusions recorded in manifest |
| All 24 protected existing repository files, including original model code, result, configurations and audits, compared using Git blob identity | PASS: byte-identical |
| Publication manifest source hashes and dispositions; exact-copy declarations | PASS |
| Membership projection | PASS: only `train_origin_ids` dropped; every retained column and row matches the original; original source SHA and transformation declared |
| Source-ledger public projection | PASS: all non-path fields unchanged; path redaction explicitly declared with original source SHA |
| Three original provider metadata projections | PASS: only original `raw_path` omitted and explicit transformation marker added; URLs, retrieval timestamps, original raw hashes and publication UNKNOWN preserved |
| Independent ZIP extraction and all extracted file hashes | PASS |
| Original saved-result verifier and public evidence verifier in isolated Python mode | PASS: saved forecast 7,552.46; 124 inventory entries and 54 active navigation links; declared aggregate arithmetic checks |
| Public candidate and ZIP hashes before/after this read-only review | PASS: unchanged |

Verification implementation: direct standard-library parsing/hash and Git-blob checks, temporary independent extraction, and only `verify_saved_result.py` and `verify_public_evidence.py`. No model code was imported or executed. The two verifier entry points are their `main` functions; no new model implementation was made for this review.

## Decision and limits

**PASS for this filtered public release**, limited to the inspected content, declared exclusions, preserved original protected artifacts, navigation, saved-result arithmetic and selected aggregate arithmetic. No unresolved exposure was found in the reviewed candidate. The four uncertainty-based exclusions are remediation records, not deleted historical evidence.

The approval does not establish unrestricted rights over excluded data or certify every possible secret pattern. Historical copied documents retain original contextual relative locators; the new public index/reference map records actual destinations and omissions. Full retraining is unavailable; original final fitted parameters and some historical logs are missing. Strict PIT, actual historical first-publication times and G4 independence remain unestablished as stated in the public scope. Shared agent rules do not provide hard technical isolation. This report is new evidence screening, not a revision of prior audits or an approval for another model run.

The sole expected follow-up content change is inclusion of this public-safe audit, followed by refreshed inventory/ZIP and rerunning both saved-evidence checks. Any other substantive change requires renewed review. This report itself contains no machine-specific absolute paths, email addresses or personal identifiers.
