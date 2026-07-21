---
name: launchpad-fix
description: Find apps installed in /Applications that don't show up in macOS Launchpad, re-register them with Launch Services via lsregister, and reset the Dock. macOS only. Use when the user says "/launchpad-fix", "fix my Launchpad", "Launchpad mi nezobrazuje aplikaci", "some apps are missing from Launchpad", or asks for help with Launchpad/Launch Services issues.
---

# launchpad-fix — procedure

Re-register macOS apps missing from Launchpad. macOS-only skill. Follow these steps in order.

## 1. Verify macOS

```
uname -s
```

If the result is not `Darwin`, stop immediately and tell the user this skill only works on macOS — the underlying tooling (`lsregister`, `mdfind`, `defaults`, the Dock) is Apple-specific.

## 2. Find missing apps

The diagnostic compares two sources:
- **What's installed:** `.app` bundles directly under `/Applications`.
- **What Spotlight knows about:** apps Launch Services has indexed as Applications.

Run this pipeline (covers both English and Czech localization of `kMDItemKind`):

```
comm -23 \
  <(ls /Applications | grep '\.app$' | sort) \
  <(mdfind "kMDItemKind == 'Application' || kMDItemKind == 'Aplikace'" -onlyin /Applications \
      | xargs -I {} basename "{}" 2>/dev/null \
      | sort -u)
```

The output is the list of app bundle names that exist on disk but Launch Services doesn't recognize — these are the ones Launchpad can't show.

Show the user the list. If it's empty, tell them Launchpad already knows about every app in `/Applications` and stop — there's nothing to fix.

Tip: if the system is in a third language (German, French, …), the `kMDItemKind` value will be that language's word for "Application". If the diff returns *everything* in `/Applications`, that's the symptom — ask the user what `kMDItemKind` value to use (they can find it with `mdls -name kMDItemKind /Applications/Safari.app`), and re-run the comparison with that value added to the `mdfind` query.

## 3. Ask which apps to register

Show the missing apps list. Then ask via `AskUserQuestion`:

- `Register all <N> apps` (recommended)
- `Pick a subset` — if there are many apps and the user wants to be selective, drop out and let them list which ones to register, or ask one app at a time if the list is short
- `Cancel`

For the "Pick a subset" path with more than ~5 apps, ask the user to list which apps to register (by index or name) rather than building a dozen `AskUserQuestion` calls.

## 4. Re-register each selected app

For each selected app, run:

```
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "/Applications/<AppName>.app"
```

Quote the path — app names commonly contain spaces. `lsregister` is silent on success and exits non-zero on failure. Collect any failures and surface them at the end (don't abort the whole batch on a single failure — keep going through the rest).

No `sudo` needed for user-readable apps in `/Applications`. If a registration fails with a permission error, mention that the user could retry with `sudo` for that specific app.

## 5. Ask before resetting the Dock

The reset closes and reopens the Dock briefly (≤ 1 second visual blip; no data loss, but any open Stack/Mission Control state is dismissed). Ask via `AskUserQuestion`:

- `Reset Launchpad now (closes and reopens Dock briefly)` (recommended)
- `Skip reset — I'll do it later` — useful if the user is in the middle of a presentation/screen recording

## 6. Reset Launchpad

If approved:

```
defaults write com.apple.dock ResetLaunchPad -bool true && killall Dock
```

`killall Dock` causes launchd to immediately restart the Dock with the `ResetLaunchPad` flag, which rebuilds the Launchpad layout from Launch Services. The flag is consumed on the next Dock launch — no cleanup needed.

## 7. Summary

Tell the user:
- How many apps were re-registered (and which, if a small number)
- Any registration failures (with the error and a suggested fix — usually `sudo` or checking the app bundle isn't damaged)
- Whether the Dock was reset
- That Launchpad will be empty for a moment after the reset, then repopulate (no action needed)
