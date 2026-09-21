# v1.7.6 — Loaded frontend verification / stale-page guard

## Status and evidence boundary

The latest reported B2/B7 attempt ran an old, already-evaluated browser module,
not the installed v1.7.4 UI. That attempt does **not** fail or pass the v1.7.4
compatibility bridge. Phase 4B remains **PARTIAL**; a valid loaded-build browser
retest is still required. The earlier version-specific failures remain historical
results. Do not convert a file SHA check, a server restart, or a workflow node's
saved `properties.ver` into evidence about the JavaScript executing in a page.

v1.7.6 adds build verification rather than another speculative lifecycle rewrite.
The v1.7.4 `loadGraphData()` bridge, sampling equations, conditioning, references,
SIGMAS, model choices and workflow graph are unchanged.

## Implemented behavior

- `GET /h3draft/ui-build` (also `/api/h3draft/ui-build` through Core's API routes)
  is a read-only, no-store build manifest. It reports UI build `1.7.6`, a backend
  process/session identifier, and SHA-256 hashes of the installed frontend files.
- The evaluated UI must report build `1.7.6`, the native state implementation,
  and an actually installed lifecycle wrapper. A diagnostic string alone does
  not certify the wrapper. The manifest must match before controls unlock.
- Draft/Continue panels show `UI 1.7.6 · VERIFIED` after a successful handshake.
  Clicking this small badge repeats verification without generation or reload.
- H3 browser requests carry the verified UI build and server-session headers.
  Missing/old headers are rejected with HTTP 409 **before the Core /prompt
  handler**, including requests sent from an old page which has no new guard JS.
- On a detected backend restart the existing page locks and requests a reload;
  a new server session never silently validates an old Preview approval.
- Only H3 Draft/Continue requests are guarded. Non-browser API clients without
  frontend headers keep the previous API contract. Explicitly supplied frontend
  headers are checked. Unrelated workflows and API calls are not modified.
- No approval is serialized. No workflow is saved, overwritten, cleared or
  reloaded automatically. No GPU work is started by verification.
- The new backend route/middleware requires a normal ComfyUI restart after update.
  No new runtime dependency is introduced: aiohttp is supplied by ComfyUI and is
  installed in CI only to exercise the real HTTP middleware tests.

This is stale-client protection, **not authentication**. Proxies must preserve
Origin/Fetch-Metadata headers for browser detection. The installed-file hashes
are diagnostics; they are not hashes of an already-evaluated JS module. The
release build stamp must change whenever a frontend compatibility release changes.

## What it cannot do

A server-side update cannot replace JavaScript already evaluated in an open page.
A one-time full page reload is required to load v1.7.6. HTTP no-store headers
prevent future cache reuse but do not hot-upgrade a live page. Do not dynamically
import another copy of the extension into the same page: duplicate callbacks and
mixed versions are not a supported recovery path.

Protect/export each unsaved workflow first. A separate test browser tab is
preferred; leave the user's working tabs alone. The uploaded legacy workflow's
saved version/widgets do not select old extension JS and are not rewritten by
this fix.

## GPU-free preflight

1. Update the node, then restart ComfyUI through the user's normal process after
   protecting unsaved work. Do not pop stashes or discard untracked files.
2. Fully load/reload a test browser page. Confirm the H3 panel badge is VERIFIED.
3. Inspect the *live* Console value, not a fresh fetch of draft.js:

```js
globalThis.__H3_DRAFT_CONTINUE_UI__
```

Expected fields:

```js
{
  loaded: true,
  version: "1.7.6",
  logicStateContract: "native",
  lifecycleBridge: "loadGraphData-wrapper", // or wrapper-existing
  frontendGuard: {
    status: "verified",
    loadedBuild: "1.7.6",
    serverBuild: "1.7.6"
  }
}
```

Read-only recheck:

```js
await globalThis.__H3_DRAFT_CONTINUE_UI__.checkFrontend()
```

A missing marker, mismatch, missing bridge or non-verified status is a **preflight
block**, not a failed B2/B7 lifecycle result. Do not run the GPU matrix yet.

## Targeted real-device retest after preflight

Use the existing fixed model/Turbo/Euler/simple/6-total/3-preview baseline.
Generate one Preview, confirm READY, and run B2's open-tab round trip. If READY
survives, continue that same Preview once to COMPLETE and run B7's round trip.
Confirm GO enabled only for READY and disabled for COMPLETE, with Queue 0/0.
Record B2/B7 separately. B3 has already passed; do not expand the matrix unless
new evidence requires it. The close/reopen approval reset remains a regression
boundary, not a license to persist backend state.

## Added automated coverage

- Real aiohttp HTTP tests: old browser requests never reach the prompt handler;
  matching builds pass without body changes; wrong sessions reject; external
  scripts and unrelated workflows remain unaffected; no-store endpoints/assets.
- JavaScript guard tests: missing/old runtime, absent actual bridge, mismatched
  server build, backend restart, incomplete installation, request preservation.
- Real extension body executed in a mocked 1.52.7-style host which does not fire
  new lifecycle hooks: loaded-build verification, READY/COMPLETE round trips,
  and close/reopen reset.

These tests do not certify real Windows/ComfyUI rendering or GPU output. They
make the previously missed host-call path testable without another GPU run.


## v1.7.6 page-local approval provenance

B10 exposed a separate boundary from stale-build verification: a verified new page must
still reject reviewed state that was not created by a Preview/GO action in that evaluated
page.

v1.7.6 assigns an in-memory page-local owner token to reviewed Draft state. Open-tab
lifecycle restore inside the same page rebinds that token. A full page reload creates a
different token, and startup/historical READY/COMPLETE reports are ignored unless a
current-page execution is pending.

This does not add persistent storage and does not alter model or sampling behavior.
