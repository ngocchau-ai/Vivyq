# [SANDBOX — KHÔNG PHẢI PRODUCTION UI] Cautreo Desktop Studio

> **[ISOLATED / SANDBOX — 2026-09-29]** UI này dùng protocol REST+SSE riêng
> (`/api/vitals`, `event: thought|token|done`), **không** nối host bus JSON-RPC
> (`ws://…/bus`) của `ui/cautreo-desktop`. Một số endpoint từng trả metrics/answer
> mô phỏng khi backend thiếu — không được coi là bằng chứng sản phẩm.
> Production surface duy nhất hiện có: `ui/cautreo-desktop` + `host/cautreo_host`.
> Xem `docs/REVIEW_SYNC_CONFLICT_AUDIT_2026-09-29.md` mục 7.

---

# Tauri + Vanilla TS (scaffold gốc)

This template should help get you started developing with Tauri in vanilla HTML, CSS and Typescript.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
