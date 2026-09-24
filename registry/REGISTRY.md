# Passport Registry v0.1.0

Opt-in builder registry. Builders register their work; the registry is the public, searchable record of who built what.

## Registration format

Each registry entry is a JSON object:

```json
{
  "builder_id": "Appel420",
  "display_name": "Derek Appel",
  "registered_at": "2026-09-24T22:30:00Z",
  "builds": [
    {
      "build_id": "sovereignty-ai-gate",
      "name": "Sovereignty AI Gate",
      "repository": "https://github.com/Appel420/Sovereignty-AI-Gate",
      "first_seen": "2026-07-13T13:19:42Z",
      "attribution": "lead"
    }
  ],
  "opt_in": {
    "training": true,
    "remixing": true,
    "redistribution": true
  }
}
```

## Opt-in controls

Builders control three dimensions:

- **training** — whether their work may be used in AI training
- **remixing** — whether their work may be remixed or derived from
- **redistribution** — whether their work may be redistributed

Default for all three: **false**. The builder must explicitly enable each.

## Registry rules

- Entries are append-only per builder (updates add, never overwrite).
- Each entry carries its own timestamp and evidence hashes.
- Removal requires the builder's verified signature.
- The registry does not rank or score builders; it records.
