# Changelog

Notable, user-visible changes to the skills in this collection, grouped by the date they landed on `main` and prefixed with the affected skill (or `repo` for collection-wide changes). Mechanical noise — typos, refactors without behavior change — is omitted; the complete history of a single skill is `git log -- skills/<name>/`.

## 2026-08-18

### Added

- **resource-busy:** new skill — cross-OS diagnosis of "who blocks this eject/unmount / who holds this file". macOS: `diskutil` stderr names the dissenting PID and its parent while the unified log never does (both verified on macOS 26.6), plus hidden Time Machine snapshot sibling mounts (21 observed at once) that make the visible volume unejectable with an empty `lsof`. Linux: `fuser -vm`/`lsof +f --` as the honest case, and the mount-namespace case where `umount` and `losetup -d` both return 0 while the device stays attached — a `/proc/*/mountinfo` sweep names the holder (verified live: dissented DMG eject; loop device held from an `unshare -m` namespace). Windows section compiled from documentation and explicitly marked untested.
- **mcp-server-adopt:** new skill for adopting a third-party MCP server end to end — candidate sweep, a single `gh api` metadata pass reporting forks next to stars, reading the source instead of trusting the README, a static security audit that must complete **before** any build or test run (`go test` executes the third-party code; a plain `go build` without cgo does not), fork-first installation, credentials kept out of the client config behind a wrapper, scope-aware registration, and verification by a real stdio `initialize` + `tools/list` handshake rather than "the process started". Delegates the MCP-specific security dimensions to `ai-security-skills:mcp-server-review` where that skill is installed, instead of duplicating it.

### Changed

- **tracker-log-entry:** step 6's `KEY=…; printf … | curl` patterns are compound commands, which the Bash guard in worktree-isolated sessions rejects as "too complex to verify"; the skill now documents the remedy — write the whole call into a scratchpad script created with the ordinary file-Write tool (so its full content is visible in the conversation before anything runs), holding the key *lookup* (never the literal), and execute it as a single plain `bash <script>`, keeping the key out of argv (v1.6.2).

### Fixed

- **repo:** frontmatter `argument-hint` values are now quoted strings in all six skills that carry the field (second-opinion, tracker-backfill, tracker-log-entry, tracker-start, work-reconcile, work-standup). Unquoted `[...]` hints parse as YAML flow sequences: four of the six failed to parse at all and were silently skipped by `npx skills add` — never installable via the CLI — and the other two parsed as one-item lists instead of strings. Claude Code tolerated every variant, which is why nothing looked broken locally.

## 2026-08-13

### Fixed

- **skillify:** the procedure for contributing a generally useful skill to the portable collection now names all three required steps — `skills/<name>/SKILL.md`, a row in the README table, and a dated line in `CHANGELOG.md`. The changelog step has been mandatory since 2026-08-04, but the skill never mentioned it, so anything contributed by following it landed unrecorded (v0.1.1).

## 2026-08-11

### Fixed

- **`tracker-*` / `work-*`:** the two suites advertised overlapping trigger phrases, so an ordinary sentence could land in the wrong skill. `tracker-stop` claimed "end session", "I'm done" and "finished working" — all of which read as the end of the working day (`work-end`) — while `tracker-start` claimed "start session", competing with the morning briefing. `tracker-backfill` and `work-reconcile` both offered to fill missing Toggl time, with nothing in either description saying which one covers the current session and which a past period. Every description now names its own scope ("the running timer", "THIS agent session", "a past period across all sessions") and points at its counterpart, and the ambiguous phrases are gone (`tracker-start`, `tracker-stop`, `tracker-backfill` v1.6.1; `work-start`, `work-end`, `work-reconcile` v0.3.1).

## 2026-08-10

### Added

- **decision-analysis:** methodology for a context-anchored decision analysis that ends in a verdict — decision rules written and dated before any evidence arrives, every load-bearing claim sourced and dated, and the durable layer kept separate from a perishable dated snapshot.

### Changed

- **launchpad-fix:** reworked from "re-register apps with `lsregister`" into a two-layer triage. A broken or empty Spotlight index — including an `mds` daemon wedged by system overload, where `mdutil -E` reports success while nothing gets indexed — now gets diagnosed and repaired separately from genuine Launch Services gaps, since `lsregister` does nothing for the former. A system-health check (load, zombies, swap) runs first because an overloaded machine cannot finish reindexing at all, and the Launchpad/Dock reset is skipped on macOS 26+, where Launchpad no longer exists.

### Fixed

- **launchpad-fix:** step 4 now states its two preconditions up front — the repairs all need `sudo` an agent cannot supply, and a volume near capacity makes every one of them a no-op. Measured on a Data volume at 98 %: a freshly restarted `mds` kept 9–28 `mdworker` processes busy for six minutes without the index growing by a single item.
- **launchpad-fix:** the step-3 triage measured `kMDItemFSSize > 0` against `/Applications`, which counts neither the app bundles (directories are skipped) nor their contents (Spotlight never indexes bundle interiors) — so it reported a healthy index as broken. Measured on macOS 26.6: 164 hits against 35 348 entries on disk, on a machine whose app index was in fact complete. Step 3 now counts apps via `com.apple.application-bundle`, compares files against a folder the user knows, and names the two false alarms that mimic a dead file index (iCloud `dataless` placeholders, Spotlight Privacy exclusions). Step 4 gained a check separating a wedged `mds` from one that is merely behind, so its repairs no longer throw away in-flight indexing work.
- **tracker-log-entry:** the macOS local-time → UTC conversion prescribed `date -j -f "<fmt>" "<in>" -u +<outfmt>`, where the trailing `-u` is not parsed as a flag: the output format was ignored and the skill fed the API a localized date string it rejected as `Invalid time format`. Replaced with an epoch round-trip, plus the two variants that fail *silently* (`-u` in front parses the input as UTC; omitting `-u` prints local time with a `Z` suffix) and why `%S` has to stay in the input format (v1.6.1).
- **code-review:** in a worktree-isolated session the findings file now goes into the worktree's own `docs.local/code-reviews/`, and copying it back into the main checkout is offered at the end of the CR — the isolation guard blocks writes into the main checkout's `docs.local/`, so the findings had nowhere to land, and a worktree copy disappears with the worktree. Reading a PR's new commits between rounds now counts as the next round's verification too: the round-N timer starts before that delta is read, so the substantive work no longer falls outside every entry while the formal round logs a misleading minute.

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
