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

```
mdfind -count -onlyin /Applications "kMDItemFSSize > 0"
mdfind -count -onlyin /System "kMDItemFSSize > 0"
```

The `/System` query is the control: that volume is read-only and its index survives most breakage.

- **/Applications ≈ 0, /System returns hundreds** → the Data-volume index is empty/broken → **Spotlight path (step 4)**.
- **Both ≈ 0** → `mds` isn't answering at all → **Spotlight path (step 4)**.
- **/Applications returns tens of thousands** → index is healthy; the complaint is about specific apps → **Launch Services path (step 5)**.

The query counts *files*, not apps, so calibrate it against the disk rather than against the number of installed apps: `find /Applications -maxdepth 4 | wc -l` finishes in seconds and gives the order of magnitude a healthy index should be reporting. An index answering a few hundred while the disk holds tens of thousands is broken, not healthy.

## 4. Spotlight path

Try the cheapest fix first and verify after each attempt (`mdfind -count -onlyin /Applications ...` should start growing within ~1 minute — app-priority workers `mdworker-application` run first):

1. **Restart the daemon:** `sudo killall mds` (launchd respawns it; `launchctl kickstart` is blocked by SIP). A daemon wedged by days of overload is the most common cause: `mdutil -E` "succeeds", workers spawn and die, the log stays silent, the index stays empty — all commands go to a brain-dead server. A fresh `mds` typically indexes all apps within a minute.
2. **If still dead — rebuild the index:** `sudo mdutil -E /System/Volumes/Data`.
3. **If still dead — recreate the store:** `sudo mdutil -a -i off && sudo rm -rf /System/Volumes/Data/.Spotlight-V100 && sudo mdutil -a -i on`, then `sudo killall mds` once more.
4. **If still dead** → reboot; if even that fails, check the filesystem (Disk Utility First Aid).

False signals to ignore:

- `mdimport -i` fails silently when `mds` is wedged (exits 0, writes nothing).
- The mtime of `/System/Volumes/Data/.Spotlight-V100` itself does not change even while contents are being rewritten — it is not a progress indicator.
- Free-space consumption is not a reliable progress indicator either.

Full-disk-volume file indexing takes hours afterwards, but apps appear in the first minute — the user's original problem is solved long before the index completes.

Verification: re-run the step-3 query (it should climb back into the tens of thousands) and spot-check `mdfind "kMDItemFSName == '<App>.app'"`.

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
