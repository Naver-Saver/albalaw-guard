# Frontend Workspace Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan. The user authorized step 1 of the agreed frontend sequence; this plan covers that step only.

**Goal:** Prepare the team repository's existing TypeScript frontend for publishing from the supplied Saver wireframe.

**Architecture:** Keep the existing React + TypeScript + Vite application and API proxy. Import the supplied design and local font, add global design variables, and document the canonical working directory. Keep the original JavaScript starter outside this checkout intact.

**Tech Stack:** Existing repository versions of React, TypeScript, Vite and oxlint; Noto Sans KR variable font.

**Spec:** User-approved step 1 in conversation; `docs/PRD.md`, `docs/spec/01-requirements.md` and `docs/CONVENTIONS.md`.

## Global Constraints

- Work on a preparation branch, never directly on main.
- Keep service credentials on the backend; use the existing `/api` proxy.
- Preserve the supplied SVG as a reference. Its application-form content will be adapted to labor-rights content in later screen work.
- Do not add common components, pages, routing or new API behavior in this step.
- This is reversible asset/configuration setup. Verify with lint, the TypeScript production build and asset checks; do not add tests that merely mirror file contents.

## Review Focus

- Original local starter and design assets remain intact.
- Font resolves from the bundled frontend output with its license included.
- Color variables match the supplied wireframe's foundation colors.
- The existing server status request and development API proxy continue to work as before.
- Documentation points to the cloned team frontend, not the old JavaScript starter.

## Task 1: Prepare the frontend workspace

**Files:** `frontend/README.md`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/styles/*`, `frontend/src/assets/fonts/*`, `frontend/src/main.tsx`, `frontend/src/index.css`, `docs/design/*`.

**Interfaces:** Preserve `fetchHealth()` and `/api` requests; expose CSS custom properties for subsequent UI work.

- [x] Clone the team repository into `albalaw-guard/` and create a preparation branch.
- [x] Install using the existing lockfile; verify the baseline with `npm run lint` and `npm run build`.
- [x] Copy the SVG and font without changing their contents; include the font license.
- [x] Connect global font and color variables while preserving the starter's layout and behavior.
- [x] Add frontend setup and design-reference documentation.
- [x] Run lint, TypeScript production build, asset hash checks and `git diff --check`.
- [ ] Review the scoped change, commit and push the preparation branch.

## Decisions

- A fresh checkout inside the writable workspace avoids overwriting the original non-Git starter and needs no extra worktree.
- Retain the existing team dependencies and lockfile versions.
- Preserve the supplied TTF; webfont compression/subsetting belongs to a later optimization if needed.
