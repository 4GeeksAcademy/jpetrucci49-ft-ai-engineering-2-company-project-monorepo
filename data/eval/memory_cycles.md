# Desk-agent memory cycles (8.5)

Evidence from isolated TinyDB runs against the compiled `desk_graph` (RAG retrieve/generate mocked). Not Qdrant. PHI was not present in either cycle.

## Cycle 1 — approve, then a later question uses it

| Step | Question | Result |
| --- | --- | --- |
| 1 | Manchester coordinator referrals (CONTEXT example 1) | Pending created; answer includes `Want me to remember this for next time?` |
| 2 | `yes` | `items` insert; pending cleared |
| 3 | `Is there a charge for cancelling 12 hours in advance?` | `generate_answer` question prefixed with the approved Manchester note |

`proposal_id`: `14fda8d4-c564-4307-b92f-4d3524f05324`

`decisions` row:

| Field | Value |
| --- | --- |
| `user_id` | 501 |
| `outcome` | `approved` |
| `run_id` | `11111111-aaaa-4111-8111-000000000502` |
| `decided_at` | `2026-09-28T19:58:10.215071+00:00` |
| `decision_message` | `yes` |
| `source_question` | At the Manchester clinic, internal referrals now go through the coordinator before the specialist — that changed last quarter. |

Approved `items` text: Manchester referrals go through the coordinator before the specialist.

Later generate prompt started with `Operator-approved notes` and included that Manchester line. RAG `context` / `context_sources` were unchanged (appointment-policy chunk only).

## Cycle 2 — reject, then a later question does not use it

| Step | Question | Result |
| --- | --- | --- |
| 1 | Austin road-closure no-show (CONTEXT example 2) | Pending created; remember prompt shown |
| 2 | `no` | Pending cleared; **no** `items` row |
| 3 | Same cancellation question as cycle 1 | Generate prompt is the bare question — no operator notes |

`proposal_id`: `5f8574d1-bb0c-4cc1-a1d4-bb32faacf799`

`decisions` row:

| Field | Value |
| --- | --- |
| `user_id` | 502 |
| `outcome` | `rejected` |
| `run_id` | `22222222-bbbb-4222-8222-000000000503` |
| `decided_at` | `2026-09-28T19:58:10.237232+00:00` |
| `decision_message` | `no` |
| `source_question` | That high no-show alert at the Austin clinic was because of a road closure that week, not a real problem with the reminder programme. |

`items` for user 502 after reject: empty. Later wrapped question was exactly `Is there a charge for cancelling 12 hours in advance?` (no road-closure note).
