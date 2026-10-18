# Unified memory registry, archive anchoring, and safe enrichment

Status: proposed architecture and operating contract; not a claim that this is fully implemented.

## Decision

Treat the source archive as an immutable evidence layer and the memory registry as a single logical index over that evidence. Do not maintain independently editable, near-identical archive and memory catalogs. Keep extracted experience as structured records that reference source messages; make it a view/index over evidence, not a second untraceable copy of history.

One physical database may contain all record types and links. Large original exports may remain in immutable object/file storage, referenced by stable archive IDs and content hashes. "One database" means one coherent registry and relationship model, not necessarily one giant file containing every byte.

## Core entities

- **ArchiveSnapshot**: stable `archive_id`, import time, source description, file hash, export/version metadata, coverage interval, import status, and known limitations.
- **Conversation**: stable `conversation_id`, archive ID(s), original source ID, title and source metadata.
- **Message**: stable `message_id` when supplied by source; also `archive_id + conversation_id + source_node_id`, timestamp as raw epoch plus normalized UTC, role, content type, parent/child edges, payload locator/hash.
- **ExperienceRecord**: stable `experience_id`, concise lesson/reason, incident class, status (candidate/verified/superseded/disputed), first/last observed time, confidence, and links to all supporting/contradicting source messages.
- **Incident**: a hypothesized real-world/agent event grouping one or more messages. It must not be equated with a keyword match.
- **Relation**: typed edges such as `supports`, `contradicts`, `same_incident_candidate`, `derived_from`, `supersedes`, `duplicate_of`, `context_before`, `context_after`.
- **ImportRun / ChangeSet**: import ID, source hash, tool/schema version, records created/linked/changed, warnings, and rollback pointer.

## Identity and addressing rules

1. Never use array position, line number, or "the 74th record" as durable identity.
2. Prefer a source-provided immutable message ID. If absent, use a deterministic key derived from archive snapshot ID, conversation ID, source node ID and raw source identity. Do not use timestamp alone: multiple messages may share a timestamp.
3. Store original IDs and original timestamp values unchanged alongside normalized values. UTC is a derived view, not a replacement for source time.
4. A source locator is a compound reference, not a mutable row offset: `archive_id + conversation_id + message_id/node_id`, plus content hash when appropriate.
5. If the source changes or IDs collide, do not silently retarget links. Mark resolution as ambiguous and require reconciliation.

## Append/enrichment workflow

1. Register each newly received archive as a new immutable snapshot; compute a hash before processing.
2. Parse into a staging area and report coverage, missing timestamps/IDs, duplicate keys, malformed nodes and overlap with existing snapshots.
3. Match conversations/messages using stable IDs first; use timestamp + normalized content + graph context only as secondary evidence.
4. For every match, preserve the old record and add provenance to the new snapshot. If two candidates are plausible, keep both and flag ambiguity.
5. Append new messages and experience candidates; do not overwrite earlier evidence. Corrected interpretations become new revisions linked with `supersedes`, leaving the old version auditable.
6. Rebuild search indexes and derived views from canonical records; indexes are disposable/re-creatable and never the sole copy of knowledge.
7. Run integrity checks, produce a diff/manifest, and only then mark the import accepted. Failed imports remain staged and can be rolled back without deleting prior records.

## Archive position drift / readdressing

Never point memory links at "record 200" or a byte/line offset that can shift after edits. Point to immutable IDs and hashes. If an archive must be rewritten, create a new snapshot ID and an explicit old-to-new mapping table:

`old_locator -> new_locator -> match_method -> confidence -> reviewer/status`.

A match based on exact stable ID can be high confidence; a match based on timestamp and similar text is only a candidate. Keep unresolved links unresolved rather than attaching experience to the wrong message. For edits, retain the old content/version and create a new revision; for additions, add new records and edges.

## Two-way retrieval

- **Context → time/source**: search a statement, error signature, decision or experience record; return supporting message IDs, UTC timestamps, archive snapshot, and surrounding graph context.
- **Time → context**: query a time interval; return messages plus parent/child branch context, related incident and linked experience records.
- **Experience → missing evidence**: take the reason a memory record was created, find earlier/later candidate incidents, classify each, then compare source evidence against the record's coverage.
- **New archive → old memory**: use overlap matching to enrich old incidents without erasing their earlier provenance, and discover novel episodes.

## Recurrence and completeness audit

Keyword frequency is only candidate generation. Group messages into candidate incidents using conversational graph, time, participants/roles, action-result pattern and semantic similarity. Distinguish user-reported symptoms, assistant hypotheses, verified failures, attempted fixes and confirmed outcomes. Then produce a coverage matrix:

- incident candidate;
- evidence messages and times;
- related existing experience IDs;
- coverage: covered / partly covered / missing / disputed;
- confidence and rationale;
- proposed memory delta.

No automatic promotion from candidate to verified memory. Repeated instances may share one root-cause lesson while remaining separate incident records. Preserve both the shared lesson and the individual episode evidence.

## Data integrity and recovery invariants

- Source snapshots are immutable and content-hashed.
- Provenance and relation edges are first-class records.
- Import is idempotent: importing the same snapshot twice must not duplicate canonical messages.
- No destructive cleanup based solely on low relevance, storage pressure, similarity or incomplete parsing.
- Every update has a change record and rollback path.
- Integrity audit detects dangling links, ID collisions, unreachable nodes, unresolved locators and records without provenance.
- A derived index can be deleted and rebuilt without losing canonical evidence.
- Existing experience remains available while new evidence is staged or uncertain.
- Incomplete recovery is represented explicitly as a coverage gap, not concealed by a "complete" flag.

## CARD111 validation plan

Use CARD111 as a test project for collection/retrieval mechanics, without assuming a full historical archive is available. Register the currently available material as one snapshot, record its coverage limitations, and exercise:

1. repeat import (idempotence);
2. add a later message/archive and verify old links remain stable;
3. edit/correct an interpretation and verify revision history;
4. resolve a message by text and retrieve exact time/source/context;
5. resolve by time and retrieve the same source message/context;
6. identify repeated failure candidates and mark covered/missing/disputed;
7. simulate a shifted/reordered export and confirm no link moves by position;
8. rebuild the derived index and verify experience/source relationships remain intact.

If a CARD111 archive arrives later, register it as another snapshot and reconcile overlap; do not reset or replace the current knowledge base.

## Implementation boundary

This document records a design decision and test contract. It does not claim that the repository currently has a production database, transactional import pipeline, semantic incident clustering, or full integrity/rollback implementation. Implement these in small, testable increments and record actual test results.
