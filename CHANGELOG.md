# Changelog

Notable, user-visible changes to the skills in this collection, grouped by the date they landed on `main` and prefixed with the affected skill (or `repo` for collection-wide changes). Mechanical noise — typos, refactors without behavior change — is omitted; the complete history of a single skill is `git log -- skills/<name>/`.

## 2026-08-11

### Fixed

- **`tracker-*` / `work-*`:** the two suites advertised overlapping trigger phrases, so an ordinary sentence could land in the wrong skill. `tracker-stop` claimed "end session", "I'm done" and "finished working" — all of which read as the end of the working day (`work-end`) — while `tracker-start` claimed "start session", competing with the morning briefing. `tracker-backfill` and `work-reconcile` both offered to fill missing Toggl time, with nothing in either description saying which one covers the current session and which a past period. Every description now names its own scope ("the running timer", "THIS agent session", "a past period across all sessions") and points at its counterpart, and the ambiguous phrases are gone (`tracker-*` v1.6.1, `work-*` v0.3.1).

## 2026-08-10

### Added

- **decision-analysis:** methodology for a context-anchored decision analysis that ends in a verdict — decision rules written and dated before any evidence arrives, every load-bearing claim sourced and dated, and the durable layer kept separate from a perishable dated snapshot.

### Changed

- **launchpad-fix:** reworked from "re-register apps with `lsregister`" into a two-layer triage. A broken or empty Spotlight index — including an `mds` daemon wedged by system overload, where `mdutil -E` reports success while nothing gets indexed — now gets diagnosed and repaired separately from genuine Launch Services gaps, since `lsregister` does nothing for the former. A system-health check (load, zombies, swap) runs first because an overloaded machine cannot finish reindexing at all, and the Launchpad/Dock reset is skipped on macOS 26+, where Launchpad no longer exists.

### Fixed

- **launchpad-fix:** step 4 now states its two preconditions up front — the repairs all need `sudo` an agent cannot supply, and a volume near capacity makes every one of them a no-op. Measured on a Data volume at 98 %: a freshly restarted `mds` kept 9–28 `mdworker` processes busy for six minutes without the index growing by a single item.
- **launchpad-fix:** the step-3 triage measured `kMDItemFSSize > 0` against `/Applications`, which counts neither the app bundles (directories are skipped) nor their contents (Spotlight never indexes bundle interiors) — so it reported a healthy index as broken. Measured on macOS 26.6: 164 hits against 35 348 entries on disk, on a machine whose app index was in fact complete. Step 3 now counts apps via `com.apple.application-bundle`, compares files against a folder the user knows, and names the two false alarms that mimic a dead file index (iCloud `dataless` placeholders, Spotlight Privacy exclusions). Step 4 gained a check separating a wedged `mds` from one that is merely behind, so its repairs no longer throw away in-flight indexing work.
- **tracker-log-entry:** the macOS local-time → UTC conversion prescribed `date -j -f "<fmt>" "<in>" -u +<outfmt>`, where the trailing `-u` is not parsed as a flag: the output format was ignored and the skill fed the API a localized date string it rejected as `Invalid time format`. Replaced with an epoch round-trip, plus the two variants that fail *silently* (`-u` in front parses the input as UTC; omitting `-u` prints local time with a `Z` suffix) and why `%S` has to stay in the input format (v1.6.1).

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
