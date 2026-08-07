# Changelog

Notable, user-visible changes to the skills in this collection, grouped by the date they landed on `main` and prefixed with the affected skill (or `repo` for collection-wide changes). Mechanical noise — typos, refactors without behavior change — is omitted; the complete history of a single skill is `git log -- skills/<name>/`.

## 2026-08-07

### Added

- **repo:** the collection is now MIT-licensed — root `LICENSE` plus `license: MIT` in every skill's frontmatter, so the license travels with per-skill copies made by `npx skills add`.

## 2026-08-04

### Added

- **work-standup:** the recap window can now be derived from `standup.default_window: "prev_standup"` plus the `schedule` block (days/time/timezone) in the work config — no more passing `--since` by hand on every scheduled stand-up (v0.4.0).

## 2026-08-01

### Added

- **kodex:** the thinking codex ships as a regular skill with an always-on pointer; the English text in `SKILL.md` is canonical, the Czech original lives in `references/kodex-cs.md`.
- **tracker-backfill:** splits the session transcript into activity blocks, so multi-day sessions backfill as separate entries.

### Changed

- **repo:** all skills moved into `skills/` (the Agent Skills standard layout) — local-path installs and symlinks created before this date point at the old locations and need re-creating.
- **repo:** skill texts are harness-neutral (actions instead of tool names, no plugin-era paths), making the collection usable beyond Claude Code; `npx skills add kratocz/skills` is the supported install path.

## 2026-07-21

### Added

- **repo:** initial import of the skills collection (Antigravity-era flat layout) with the README skills table; kodex gains the explicit Git rule (no `git add .`).
