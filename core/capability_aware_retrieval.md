# Capability-aware adaptive source search

## Why this exists

Search is a constrained planning problem, not a flat scan of every location. A source can be relevant but unable to contain the requested item under known constraints; another source can be plausible but poorly described. The planner uses known capabilities and limits to order search, while retaining a controlled fallback path for misplaced items and incorrect metadata.

The physical analogy is deliberate: do not start by searching for a large object in a tiny drawer when larger locations are available. But do not permanently rule out the tiny drawer, because real-world storage metadata and people's placement behavior can be wrong.

## Search tiers

1. **Preferred** — known source profile matches requested source type, format, project, capabilities, and applicable size limits.
2. **Fallback** — no known conflict, but one or more relevant properties are unknown. Unknown does not mean incompatible.
3. **Emergency** — known metadata conflicts with the request or marks the source inaccessible. Search this tier only after earlier tiers fail to verify identity.

Within a tier, use configured priority, then stable configuration order. Priority changes order, not truth or evidence strength.

## Adaptive expansion rule

Search one source at a time in tier order. Stop early only when the exact content hash or a stable ID in a declared identity field verifies a match. A text-only candidate does not stop the search: continue to later sources and tiers, because the real item may still be elsewhere. If no verified match is found, report unverified candidates separately and state whether all configured tiers were scanned.

## Metadata model

Each source profile may describe:
- stable \`source_id\` and local \`root\`;
- \`source_types\`, \`formats\`, and \`project_ids\`;
- \`capabilities\` (for example \`source_records\`, \`attachments\`, \`full_text\`, \`version_history\`);
- \`min_item_size_bytes\` and \`max_item_size_bytes\`;
- \`accessible\` and numeric \`priority\`.

The request may supply:
- \`identity\`, \`expected_sha256\`, or \`query\`;
- \`source_type\`, \`format\`, \`project_id\`, \`required_capabilities\`;
- \`size_bytes\`.

This is an initial extensible profile, not a complete ontology of all possible sources. Unknown fields are not inferred. Source profiles must be grounded in observed metadata or explicitly labelled estimates.

## Use

Create a JSON catalog such as:

~~~json
{
  "sources": [
    {
      "source_id": "project-memory",
      "root": "./",
      "source_types": ["structured_export"],
      "formats": ["json", "jsonl"],
      "project_ids": ["AGENT_MEMORY_SYSTEM"],
      "capabilities": ["source_records", "version_history"],
      "min_item_size_bytes": 0,
      "max_item_size_bytes": 10000000,
      "accessible": true,
      "priority": 10
    }
  ]
}
~~~

Create a request JSON with a stable ID/hash or text query, plus known constraints. Then run:

~~~bash
python3 tools/adaptive_source_search.py --catalog source_catalog.json --request request.json --expected-path registry/source_records.jsonl
~~~

Use \`--plan-only\` to inspect the proposed order without scanning files.

## Implementation boundary

\`tools/adaptive_source_search.py\` plans and executes tiered searches across explicitly configured **local filesystem roots**. It delegates per-root discovery to \`tools/relocation_aware_discovery.py\`. It does not yet query remote GitHub branches, connected apps, devices, or arbitrary external archives; those require source adapters and their own availability, permission, cost, freshness, and provenance metadata.

The tool is not automatically invoked by ChatGPT. A runtime must call it or implement the same policy. No files are moved, no pointers rewritten, and no candidate is promoted to approved memory.

## Acceptance criteria

- Known-compatible sources are searched before sources with unknown profiles.
- Known-conflicting sources are retained in an emergency tier, not silently deleted from the search universe.
- Unknown metadata causes fallback, not automatic exclusion.
- Text candidates do not stop search; a verified identity match does.
- No-match is reported only within the configured sources and scan bounds.
- Search is read-only and deterministic for the same catalog, request, and filesystem state.
