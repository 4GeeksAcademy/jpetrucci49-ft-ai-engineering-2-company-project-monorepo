# Desk-agent memory

TinyDB file store for **operator** notes. Not RAG, not Qdrant, not `healthcore_knowledge`.
LangGraph `MemorySaver` is the graph checkpointer only.

| File | Role |
|------|------|
| `phi.py` | HIPAA + UK GDPR identifier scan (`contains_phi`) |
| `store.py` | `read` / `propose` / `resolve` / `log_phi_discard` |
| `classify.py` | `approve` / `reject` / `edit` / `unclear` (not `"yes" in message`) |
| `propose.py` | Self-eval: should this turn become a pending proposal? |
| `consolidate.py` | Cap 20, 90-day TTL, exact-text+kind+user dedupe |

Pending proposals expire after **24 hours**. One pending row per `user_id`. PHI never lands in `items`; discarded PHI is `[redacted]` in `decisions`.

Path: `AGENT_MEMORY_DB_PATH` or `services/api/agent_memory.json`.

## Must not propose

1. “What's this week's no-show rate?” — one-off dashboard figure.
2. “Patient Johnson cancelled tomorrow's appointment, note that down.” — PHI; the user-visible answer must refuse, not skip silently.
3. “Thanks, that settles my report.” — closing, nothing new.
4. Ticket/status or stock lookup only, empty/refuse/weather, pure policy Q&A with no clinic-specific correction.
5. User-asserted fee / Medicare / Medicaid / treatment overrides of the knowledge base.

## Should propose

Manchester coordinator referrals; Austin road-closure no-show (not the reminder programme); Diane Foster vacancies by **role**.

## Consolidation

On every successful `items` write, and on `read` when a user is over cap:

- Keep at most **20** items per `user_id` (oldest `updated_at` dropped first).
- Dedupe `user_id` + `kind` + normalized text; keep the newest.
- Drop rows older than **90 days** from `updated_at`.
- Run `contains_phi` again before upsert; drop on hit.
