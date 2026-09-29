# RFP intake pipeline (`rfp_intake`)

Dedicated LangGraph for Milestone 9 Part 1. Not mixed into the CX `desk_graph`.

```text
START → convert → classify
  not an RFP → persist_discarded → END
  valid RFP  → orchestrate → revenue | clinical | compliance (parallel)
            → synthesize → persist_complete → END
```

| Status | Meaning |
| --- | --- |
| `analyzing` | Upload accepted; graph running |
| `discarded` | Classifier reject (`not_an_rfp`) or crash (`pipeline_error`) |
| `intake_complete` | Synthesizer persisted; Sales can read key aspects |

**Convert:** MarkItDown PDF→Markdown, `contains_phi` + `[REDACTED]`, `py-readability-metrics` on the redacted text, write `data/raw/rfp/{ticket_id}.md`.

**Handoff** (`rfp_tickets.handoff_json`) for Part 2 — do not re-parse the PDF:

```json
{
  "ticket_id": "<uuid>",
  "phi_detected": false,
  "metadata": {},
  "departments": [{"department_id": "revenue", "owner": "Tom Callahan", "key_aspects": [], "open_questions": []}],
  "synthesizer_summary": "what to ask whom"
}
```

Always three departments: `revenue`, `clinical`, `compliance`. HTTP routers only trigger/query this package.
