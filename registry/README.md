# Canonical source registry

`source_records.jsonl` is the shared, append-only registry for source-message metadata. The file is created only by an explicit `tools/source_evidence_registry.py --apply` operation.

- It stores source locators, source and parser hashes, source-message timestamps, message/node relationships and attachment-presence metadata.
- It does **not** store message text, conversation titles, author names or `project_id`. Raw-source ingestion must not decide which project a message belongs to.
- `source_record_id` identifies a stable source locator. A source snapshot hash and parser version identify a particular extracted revision.
- Exact replay of the same source record/snapshot/parser revision is a no-op. A new snapshot or parser version is appended as another revision; prior rows are never overwritten.
- `source_time` is the timestamp supplied by the source export. It is not a semantic `event_time`.
- The JSON Schema is `schemas/source_record.schema.json`; the shared identity/validation code is `tools/source_registry_contract.py`.

The intake planner is still a dry-run planner. This writer currently implements only the `source_records → source_evidence_registry.append_source_records` route; source-inventory and raw-source-reference routes remain unimplemented and must not be treated as executable.
