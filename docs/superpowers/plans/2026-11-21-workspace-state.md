# Workspace State Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline and request one final branch review.

**Goal:** Keep document work through sidebar navigation while gating unavailable steps.

**Architecture:** Keep the upload component mounted but hidden within Workspace; its in-memory file, language, preview and consent survive sidebar navigation. Workspace owns review drafts and result caches already; stop clearing these on upload navigation. Explicit reset/file changes invalidate review data, while language changes keep drafts and revoke confirmation/results. No browser or server persistence is added.

**Tech Stack:** React, TypeScript, Vite, Node test runner, happy-dom for real client lifecycle tests.

## Accepted behavior

User approved the proposed table: sidebar navigation preserves work; edit/results require extraction; results before confirmation routes to edit; file replacement/deletion and new-document action clear prior work. Refresh, tab close or leaving Workspace releases its memory. Question/recording sections remain independent. Hide navigation hints as text below disabled buttons. Abort OCR when leaving upload so background completion cannot unexpectedly switch sections.

## Tasks

- [x] Add failing client tests for upload/English retention, edit draft/result return, step gating and explicit reset/replacement.
- [x] In App.tsx retain upload mount, remove navigation reset, add invalidation and new document handlers, and guard step transitions.
- [x] In DocumentUploadPage.tsx notify file/type/language changes; cancel in-flight OCR on hiding; offer resume after extraction; update privacy text.
- [x] In AppLayout.tsx mark unavailable steps and expose new-document action; add accessible disabled styling.
- [x] Run client lifecycle regressions, full frontend tests, lint/build, diff checks and final read-only review.
- [x] Commit and push on issue #87 branch and create PR using repository template; report deployment status accurately.
