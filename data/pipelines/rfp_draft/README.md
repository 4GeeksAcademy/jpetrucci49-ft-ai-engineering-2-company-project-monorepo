# RFP draft pipeline (`rfp_draft`)

Dedicated LangGraph for Milestone 9 Part 2. Not mixed into `desk_graph` or `rfp_intake_graph`.

```text
START → assign
      → revenue | clinical | compliance generate (parallel)
      → under_evaluation
      → readability | relevance | compliance eval (parallel, disjoint eval_parts)
      → combine_eval
      → all pass or iteration cap → persist → END
      → some fail and iteration < 3 → generate failing departments only → eval again
```

| Status | Meaning |
| --- | --- |
| `intake_complete` | Part 1 done; Part 2 has not started |
| `drafting` | Assignment + generators running |
| `under_evaluation` | Evaluators / revise loop; **also** the all-pass resting status |
| `needs_human_review` | At least one section hit `MAX_DRAFT_ITERATIONS = 3` without `overall_pass` |

Part 2 is finished when `rfp_tickets.part2_handoff_json` is set. That payload is what Part 3 reads — do not overwrite Part 1 `handoff_json`.

**Generators** consume only `handoff_json` (metadata + that department’s `key_aspects` / `open_questions` / owner). They do not re-read the PDF.

**Loop cap:** first draft + up to two revisions. Capped failures stay in `part2_handoff_json` with `needs_human_review: true`. Eval fail never sets `discarded`. Crash sets `error_code=draft_pipeline_error` and leaves `drafting` or `under_evaluation`.

HTTP routers only trigger/query this package (`POST /rfp/tickets/{id}/draft` → 202).
