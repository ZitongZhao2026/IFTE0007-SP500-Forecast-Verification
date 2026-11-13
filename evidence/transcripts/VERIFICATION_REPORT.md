# Archival verification, pending independent read-only review

- Captured Codex source rollout SHA-256 `defd505e09c8502ef5d2ab21ff7d3c122516ef75016db1dc47592caf80c85966`. Eleven selected JSONL line numbers were parsed. Each selected field is an exact substring of its cited original event. Skipped data are shown as `[omitted]` in the report extract.
- Seven supporting project records in Eva's package and twelve in the local archive are byte-identical copies. Source and exported-copy hashes are indexed separately.
- The ZIP was reopened, passed `testzip`, and each member matched its local package file byte for byte.
- The package intentionally excludes raw CRSP CSVs, CRSP-derived row-level tables and the full unredacted Codex rollout. This verification is an integrity check, **not** a re-run of historical research.
- Independent read-only conclusion must be appended after a separate reviewer checks quotes, roles, dates, redaction and file classification. Until then the status is `PENDING_INDEPENDENT_REVIEW`.
