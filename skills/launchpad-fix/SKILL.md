---
name: launchpad-fix
description: Triage and fix macOS apps not being offered when launching. Distinguishes a broken/empty Spotlight index (incl. a wedged mds daemon) from apps genuinely missing from Launch Services, fixes the right layer (killall mds / reindex vs lsregister), and resets Launchpad only where it still exists (macOS < 26). Use when the user says "/launchpad-fix", "macOS nenabízí aplikace", "Spotlight nenachází aplikace", "apps not showing in Spotlight", "fix my Launchpad", "Launchpad mi nezobrazuje aplikaci", "some apps are missing from Launchpad", or asks for help with app-launcher/Spotlight/Launch Services issues.
license: MIT
---

# launchpad-fix — procedure

Fix macOS apps that aren't offered when the user tries to launch them. macOS-only skill.

Two different layers can cause this symptom, and they need opposite fixes:

- **Spotlight index** — on macOS 26+ there is no Launchpad; apps are offered by Spotlight from the Data-volume index. A broken/empty index (or a wedged `mds` daemon) makes *all* apps disappear. `lsregister` does NOT help here.
- **Launch Services** — individual apps missing from an otherwise healthy launcher. This is the `lsregister` case.

Follow the steps in order — the triage in step 3 decides which path applies.

## 1. Verify macOS

```
uname -s && sw_vers -productVersion
```

If not `Darwin`, stop — the tooling (`mdfind`, `lsregister`, `mdutil`) is Apple-specific. Remember the version: the Launchpad/Dock-reset step at the end only applies below macOS 26.

## 2. System health FIRST

An overloaded machine cannot finish (re)indexing — diagnosing Spotlight on a starved system wastes hours chasing the wrong cause. Check:

```
uptime
ps -Ao stat | grep -c '^Z'
sysctl -n vm.swapusage
```

Red flags: load per core >> 1, hundreds of zombies, swap nearly full. If present, fix capacity first and only then continue:

- zombies → find the parent: `ps -Ao ppid,stat | awk '$2 ~ /^Z/ {print $1}' | sort | uniq -c | sort -rn`, then `kill <PPID>` (launchd reaps the orphans in seconds; a known repeat offender is Pioneer `FwUpdateManagerd`, which runs under the user — no sudo needed)
- full swap / no free RAM → close browsers and other heavy apps
- nearly full disk → free space; note that deleted space stays held by APFS local snapshots until `sudo tmutil deletelocalsnapshots /`

## 3. Triage: which layer is broken?

Apps and files are indexed independently and fail independently, so measure both.

**Apps** — this is what the launcher actually offers:

```
mdfind -count "kMDItemContentType == 'com.apple.application-bundle'"
mdfind -count -onlyin /Applications "kMDItemContentType == 'com.apple.application-bundle'"
```

Compare the second number against `ls /Applications | grep -c '\.app$'`. They will not match exactly — the index also counts `.app` bundles nested inside other folders, so it usually lands slightly higher. Same ballpark means the app index is fine.

**Files** — compare a folder you know against the index:

```
find ~/Downloads -type f | wc -l
mdfind -count -onlyin ~/Downloads "kMDItemFSSize > 0"
```

**Do not run the file comparison against `/Applications`.** `kMDItemFSSize > 0` skips directories — and an `.app` bundle *is* a directory — while Spotlight never indexes bundle interiors as separate items. The count there measures stray log files and icons sitting loose in `/Applications`, not index health. Measured on a healthy macOS 26.6 machine: 164 hits against 35 348 entries from `find -maxdepth 4`. That ratio looks catastrophic and means nothing.

Routing:

- **App count ≈ 0** → the app index is gone → **Spotlight path (step 4)**.
- **App count healthy, specific apps missing** → **Launch Services path (step 5)**.
- **App count healthy, file count far below the disk** → the file index is incomplete → step 4 applies, but rule out the two false alarms below first.

Two things look like a broken file index and are not:

- **iCloud placeholders.** A file synced to iCloud Drive and evicted locally is `dataless` — its body is not on disk, so there is nothing to index. `stat -f '%Sf' <file>` prints `compressed,dataless`, and `mdls` returns `(null)` for every attribute including `kMDItemFSName`. Under Desktop & Documents sync a folder can be mostly placeholders; near a full disk macOS evicts aggressively and large files go first. Measured on one such machine: 156 of 335 PDFs in `~/Documents` were placeholders.
- **Spotlight Privacy exclusions.** System Settings → Spotlight → Search Privacy. An excluded folder is not a broken index.

## 4. Spotlight path

Two preconditions before touching anything.

**Every repair below needs `sudo`.** An agent in a non-interactive shell cannot supply the password — hand the commands to the user to run, and resume measuring once they report back.

**Check free space.** Spotlight needs room to write, and on a volume near capacity every repair below runs without the index ever growing. Measured on macOS 26.6 with the Data volume at 98 % (48 GB of 1 995 GB): a freshly restarted `mds` kept 9–28 `mdworker` processes busy for six minutes while the item count did not move by one. Run `df -H /System/Volumes/Data` — above roughly 95 %, free space first, or you are diagnosing a store with nowhere to grow. Note this cuts the other way too: reclaiming space can take a while to show up, because deleted files stay held by APFS local snapshots until `sudo tmutil deletelocalsnapshots /`.

Try the cheapest fix first and verify after each attempt (the step-3 app count should start growing within ~1 minute — app-priority workers `mdworker-application` run first):

1. **Restart the daemon:** `sudo killall mds` (launchd respawns it; `launchctl kickstart` is blocked by SIP). First confirm it is actually wedged rather than merely slow: `ps -Ao pid,etime,%cpu,comm | grep -E 'mds|mdworker'` — live `mdworker_shared` processes a few minutes old and a `mdfind` that returns *some* hits mean the daemon is answering and indexing, just not keeping up, in which case restarting it only throws away in-flight work. A genuinely wedged daemon: `mdutil -E` "succeeds", workers spawn and die, the log stays silent, the index stays empty — all commands go to a brain-dead server. A fresh `mds` typically indexes all apps within a minute.
2. **If still dead — rebuild the index:** `sudo mdutil -E /System/Volumes/Data`.
3. **If still dead — recreate the store:** `sudo mdutil -a -i off && sudo rm -rf /System/Volumes/Data/.Spotlight-V100 && sudo mdutil -a -i on`, then `sudo killall mds` once more.
4. **If still dead** → reboot; if even that fails, check the filesystem (Disk Utility First Aid).

False signals to ignore:

- `mdimport -i` fails silently when `mds` is wedged (exits 0, writes nothing).
- The mtime of `/System/Volumes/Data/.Spotlight-V100` itself does not change even while contents are being rewritten — it is not a progress indicator.
- Free-space consumption is not a reliable progress indicator either.

Full-disk-volume file indexing takes hours afterwards, but apps appear in the first minute — the user's original problem is solved long before the index completes.

Verification: re-run the step-3 queries — the app count should come back to roughly the number of installed apps — and spot-check `mdfind "kMDItemFSName == '<App>.app'"`.

## 5. Launch Services path (healthy index only)

Find apps present on disk but unknown to Launch Services (covers English and Czech localization of `kMDItemKind`):

```
comm -23 \
  <(ls /Applications | grep '\.app$' | sort) \
  <(mdfind "kMDItemKind == 'Application' || kMDItemKind == 'Aplikace'" -onlyin /Applications \
      | xargs -I {} basename "{}" 2>/dev/null \
      | sort -u)
```

Symlinks in `/Applications` are this pipeline's blind spot: it matches `ls` names against `basename` of the paths `mdfind` returns, and for a symlink the two need not agree. Observed on macOS 26.6: `Safari.app` (a symlink into the Cryptexes) does come back as `/Applications/Safari.app` and matches fine, but one whose name differs from its target bundle (`GPT4All.app → gpt4all/bin/gpt4all.app`) has no such guarantee. Check anything suspicious with `ls -l /Applications/<App>.app` before acting on it — registering a symlink is a no-op at best.

Interpreting the result:

- **Empty** → Launch Services knows every app; nothing to fix.
- **A few apps** → genuine registration gaps; continue below.
- **Everything (or nearly everything)** → NOT hundreds of unregistered apps. Either the Spotlight index is dead after all (go back to step 3/4) or, if the index is provably healthy, the system runs in a third language — find the right `kMDItemKind` value via `mdls -name kMDItemKind /Applications/Safari.app` and re-run with it added.

Show the list and ask the user to choose: register all / pick a subset / cancel. Then for each selected app:

```
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "/Applications/<AppName>.app"
```

Quote the path (spaces are common). `lsregister` is silent on success. Collect failures and report them at the end (a permission failure → suggest retrying that one with `sudo`); don't abort the batch.

## 6. Launchpad reset — macOS < 26 only

macOS 26 removed Launchpad (apps are offered by Spotlight), so this step is a no-op there — skip it and say so. On older macOS, ask first (the Dock briefly restarts; ≤1 s visual blip):

```
defaults write com.apple.dock ResetLaunchPad -bool true && killall Dock
```

## 7. Summary

Tell the user: which layer was broken and what fixed it; how many apps were re-registered (Launch Services path) or how the index was revived (Spotlight path); any failures with suggested fixes; whether a Dock reset ran; and — on the Spotlight path — that full file indexing continues in the background for hours while apps already work.
