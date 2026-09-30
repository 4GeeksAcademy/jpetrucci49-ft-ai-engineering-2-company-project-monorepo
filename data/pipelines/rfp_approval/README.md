# RFP approval (`rfp_approval`)

Dedicated LangGraph for Milestone 9 Part 3. Not mixed into `desk_graph`, `rfp_intake_graph`, or `rfp_draft_graph`.

Each department is its own checkpoint thread: `rfp-{ticket_id}:{department_id}`. The parent join uses `rfp-{ticket_id}` and does not call `interrupt`.

| Status | Meaning |
| --- | --- |
| `waiting_for_approval` | At least one department has not approved |
| `done` | `final_document_json` stored after all three owners approve |

Approvers stored on the section are Tom Callahan, Dr. Marcus Reid, and Claire Whitfield. `request_changes` revises only that department, up to `MAX_APPROVAL_ITERATIONS = 3`. Checkpoints live in `data/raw/rfp_approval.sqlite`.
