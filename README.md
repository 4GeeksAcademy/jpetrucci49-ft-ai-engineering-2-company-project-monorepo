# HealthCore Monorepo

HealthCore project workspace containing:

- Public multipage website (`index.html`, `application.html`, `utility-test.html`)
- Frontend language toggling (English/Spanish)
- TypeScript utility modules in `src/utils`
- Unit tests and fixtures in `tests/utils`
- Manual utility function tester UI (`utility-test.html`)

## Quick Start

1. Install dependencies:

```bash
npm install
```

2. Build frontend assets:

```bash
npm run build:css
npm run build:utility-test
```

3. Run local static server:

```bash
npm run start
```

Default local URL: `http://localhost:4173`

## Development Workflow

- Rebuild Tailwind output after UI changes:

```bash
npm run build:css
```

- Rebundle utility tester after edits to `src/utility-test.ts` or `src/utils/*`:

```bash
npm run build:utility-test
```

- Type-check TypeScript:

```bash
npm run typecheck
```

- Run tests:

```bash
npm test
```

- Run utility playground script:

```bash
npm run utils:playground
```

## Key Scripts

- `npm run start`: Serve repository as static site on port 4173
- `npm run build:css`: Compile `styles/tailwind.css` to `assets/css/tailwind.css`
- `npm run build:css:watch`: Watch mode for Tailwind CSS
- `npm run build:utility-test`: Bundle `src/utility-test.ts` to `assets/js/utility-test.js`
- `npm run typecheck`: Run TypeScript checks
- `npm test`: Execute Vitest suite

## Deployment

This project deploys as a static site.

### Build Step (required)

Run this before every deployment:

```bash
npm install
npm run build:css
npm run build:utility-test
```

### Deploy Artifacts

Deploy the repository root as static files, including generated assets:

- HTML pages (`index.html`, `application.html`, `utility-test.html`)
- `assets/css/tailwind.css`
- `assets/js/utility-test.js`
- `language-toggle.js`
- `validation.js`
- Any referenced files under `assets/`

### Platform Notes

- Netlify: publish directory `.` (repository root)
- Vercel static: configure output directory as `.`
- GitHub Pages: publish built branch contents with generated asset files committed or built in CI

## Repository Areas

- `src/`: TypeScript source modules and utility tester source
- `tests/`: Vitest test suites and fixtures
- `assets/`: Built frontend assets and static resources
- `styles/`: Tailwind source stylesheet

## Language Support

The public pages and utility tester support English and Spanish via data attributes and `language-toggle.js`.
