# Frontend structure

Both Vite apps share a similar layout to keep components predictable.

- `src/pages`: top-level views rendered by the router/App
- `src/components`: reusable UI blocks (lists, panels, forms)
- `src/hooks`: custom hooks that encapsulate side effects such as API polling or WebSocket streaming
- `src/services`: simple API clients/wrappers for fetch/WebSocket helpers
- `src/utils`: date/number helpers shared inside each app
- `src/assets`: static imagery/audio (currently empty placeholders)

Session app focuses on live meeting telemetry for participants, while Admin app handles CRUD-style meeting management and summaries.
