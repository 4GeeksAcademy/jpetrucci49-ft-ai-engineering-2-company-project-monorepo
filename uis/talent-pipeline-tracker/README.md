# HealthCore Talent Pipeline Tracker

Internal People & Talent UI for managing the Executive Assistant recruitment pipeline (Milestone 3).

## Stack

- Next.js 16 (App Router)
- React 19 + TypeScript
- Tailwind CSS v4

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run start` | Run production server |
| `npm run lint` | ESLint |

## Environment

| Variable | Example |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://playground.4geeks.com/tracker/api/v1` |

## Auth and password recovery (M8/M9)

Same auth routes as backoffice: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/account/profile`, `/account/change-password`.

For reset emails to open this app, set `PASSWORD_RESET_URL=http://localhost:3002/reset-password` in `services/api/.env`. Testing steps: root [`README.md`](../../README.md#testing-password-recovery-and-change-m9).
