# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

## Architecture

- [ARCHITECTURE_PROPOSAL.md](./ARCHITECTURE_PROPOSAL.md) — HealthCore backend pattern, FastAPI structure, domain routers, monorepo FE/BE considerations

## Security

- [security/11.5_OWASP_AUDIT.md](./security/11.5_OWASP_AUDIT.md) — OWASP Top 10:2025 audit
- [security/12_NIST/README.md](./security/12_NIST/README.md) — model input map and AI-system inventory (NIST report follows)

## Observability

- [telemetry/telemetry-plan.md](./telemetry/telemetry-plan.md) — Telemetry Plan (catalogue, envelope, delivery)
- [telemetry/event-schemas.json](./telemetry/event-schemas.json) — Event envelope and per-type JSON Schema (draft-07)
- [../data/pipelines/PIPELINE_DESIGN.md](../data/pipelines/PIPELINE_DESIGN.md) — Monthly clinic supply performance pipeline (design)

> _Spanish version: [README.es.md](./README.es.md)._
