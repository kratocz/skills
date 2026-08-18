---
name: resource-busy
description: "Use when a disk/volume refuses to eject or unmount, or a file/directory cannot be deleted or modified because something holds it — symptoms \"Resource busy\", \"Unmount was dissented\", Finder \"disk in use\", Linux \"umount: target is busy\", EBUSY, a loop/block device still attached after umount, Windows \"file is in use by another process\"; or the user says \"nemůžu vysunout disk\", \"disk nejde odpojit\", \"nejde smazat soubor, je používaný\", \"kdo drží ten soubor\", \"can't eject my drive\". Finds the culprit process, including holders invisible to lsof/fuser (hidden Time Machine snapshot mounts, Linux mount namespaces/containers, Windows handles). Not for media that fails to MOUNT or shows as unreadable/damaged — that is macos-disk-not-mounting."
license: MIT
---

# resource-busy — procedure

Two entry shapes, one toolbox:

- **A volume/device won't eject or unmount** — start at the OS playbook below.
- **A single file/directory can't be deleted, moved, or overwritten** — same tools, pointed at the path instead of the mount.

Work the ladder top-down: **identify → stop gracefully → force only when quiesced**. Never start at force.

Identification steps are read-only, with one deliberate exception: re-attempting the unmount/eject itself — that is both the reproduction and, on macOS, the command that names the culprit. Everything that changes state (stopping holders, force detaches, kills) belongs to the resolution rungs behind the Safety rules.

## macOS

1. **Reproduce from a terminal, not Finder.** Finder's "disk in use" dialog hides the culprit; `diskutil`'s error names it, including the parent (verified macOS 26.6):

   ```
   $ diskutil eject disk7
   Unmount of disk7 failed: at least one volume could not be unmounted
   Unmount was dissented by PID 47781 (/usr/bin/tail)
   Dissenter parent PPID 47778 (/bin/zsh)
   ```

   For one volume of a multi-volume disk use `diskutil unmount /Volumes/NAME`; for the whole device `diskutil unmountDisk diskN`. Identify `diskN` by UUID/name via `diskutil info /Volumes/NAME` first — device numbers change between connections.

2. **Do not chase the dissenter PID in the unified log — it is not there.** Verified on macOS 26.6: `log show --predicate 'sender == "diskarbitrationd"'` records the attempt and `unable to unmount … (status code 0x00000010)`, but never the dissenting PID. The log tells you *what* was attempted and *when* (useful after a silent Finder failure); only `diskutil` stderr names *who*.

3. **Open files on the volume:** `sudo lsof /Volumes/NAME` (a mount-point argument selects the whole filesystem). For a single stuck file: `sudo lsof /path/to/file`. Empty output does **not** clear the volume — dissenters and sibling mounts (next steps) never appear in lsof.

4. **Hidden sibling mounts of the same physical disk.** Time Machine mounts backup snapshots read-only under `/Volumes/.timemachine/<UUID>/…` — a real backup disk was observed holding **21** such mounts at once while Finder showed a single volume. Ejecting the visible volume fails while they exist, and lsof on the visible path shows nothing.

   ```
   mount | grep diskN        # every mount backed by the device, hidden ones included
   ```

5. **Dissenter is a daemon, not an open file.** Typical: `backupd` (Time Machine running — stop with `tmutil stopbackup`, check `tmutil status`), `mds`/`mdworker` (Spotlight indexing the volume — check `mdutil -s /Volumes/NAME`), `fseventsd`, QuickLook. Stop the *operation* (or wait it out); do not `kill -9` system daemons as a first move.

6. **Escalate:** `diskutil unmountDisk force diskN` detaches every volume of the device, hidden mounts included, then `diskutil eject diskN`. Force is safe only when nothing is writing — never force out an in-progress backup or copy; stop it first (in-flight writes are lost, and USB bridges with volatile write caches can tear filesystem structures).

## Linux

1. **`umount: target is busy`** — the honest case. Two finders, run both (verified, Debian):

   ```
   $ fuser -vm /mnt/x                     # ACCESS: c=cwd, e=exe, m=mmap, r=root, f=open file
                        USER   PID ACCESS COMMAND
   /mnt/x:              root   276 ..c..  sleep
   $ lsof +f -- /mnt/x                    # +f -- forces filesystem interpretation
   COMMAND PID USER  FD  TYPE DEVICE NAME
   sleep   276 root cwd   DIR  0,122 /mnt/x
   ```

   Also check child mounts: `findmnt -R /mnt/x` — a submount blocks its parent. Then stop the holder and retry.

2. **The invisible case: every command "succeeds", yet the device stays busy.** Verified end to end: with the mount copied into another mount namespace, `umount` in your namespace returns 0 (it only detaches *your* view), `lsof` finds nothing, `fuser` on the now-unmounted path reports the *parent* mount (garbage), and `losetup -d` returns 0 **while the device remains attached** — detach is deferred, which `losetup -a` reveals. The only tool that names the holder is a mountinfo sweep across all processes:

   ```
   $ grep -l /dev/loop0 /proc/[0-9]*/mountinfo
   /proc/294/mountinfo                     # → cat /proc/294/comm, ps 294
   ```

   Search by device (`/dev/sdb1`, `/dev/loop0`) or by mount path, and run the sweep as root — `/proc/<pid>/mountinfo` of other users' processes is not readable otherwise. Typical holders: containers started before/while the mount existed, systemd services with `PrivateMounts=`/`ProtectHome=` (their namespace snapshots mounts at service start — `systemctl restart` releases), a leftover `unshare -m`. Stop that process/container/service; deferred detaches then complete on their own (re-check with `losetup -a` / `lsblk`).

3. **Other silent holders** when both finders are empty: the kernel itself — NFS export (`exportfs -v`), swapfile on the volume (`swapon --show`), loop device backed by a file on it (`losetup -a`), or a dm/LVM/LUKS layer stacked on the block device — `ls /sys/block/<dev>/holders/` (verified: a dm target shows as `dm-0` there, and `losetup -d` keeps "succeeding" without releasing until `dmsetup remove`/`cryptsetup close`/`vgchange -an` tears the layer down).

4. **Escalate:** `umount --lazy` hides the mount but releases nothing until holders exit — it is a scheduling tool, not a fix, and makes later diagnosis harder (the path is gone, holders remain). Prefer finding the holder. Force (`umount -f`) is for hung network filesystems.

## Windows

**Untested — compiled from vendor documentation (2026-08); verify output formats on a real machine before relying on them.**

1. Sysinternals `handle.exe -a -u "C:\path\or\D:"` — the canonical "who holds it" (run elevated).
2. Safe-removal refused: Event Viewer → *Windows Logs → System*, source **Kernel-PnP**, event **225** — names the blocking process ID.
3. Resource Monitor (`resmon`) → CPU tab → *Associated Handles* → search the path. GUI equivalent of handle.exe.
4. `openfiles /query` — **empty by default**; requires `openfiles /local on` + reboot beforehand, so it only helps if enabled in advance.
5. Usual suspects: Explorer preview pane/thumbnails, antivirus scan, Search indexer, OneDrive/sync clients.

## Safety rules

- Before killing anything, show the user what holds the resource and let them decide — a "blocker" may be their unsaved work or a running backup.
- Force-unmount only when nothing writes to the device. After any force, prefer re-checking the filesystem before trusting it again (`fsck_apfs -n -l` / `fsck`).
- The prevention for external disks is behavioral: **eject/unmount before unplugging, every time.** Drives behind USB bridges commonly run volatile write caches; hard unplugs tear in-flight filesystem updates, and the damage surfaces months later when the block is finally read.

## Common mistakes

| Mistake | Reality |
|---|---|
| Trusting the Finder/GUI "in use" dialog | It omits the PID; terminal `diskutil` names dissenter and parent |
| Grepping the unified log for the dissenter | Not logged (verified macOS 26.6) — only `diskutil` stderr has it |
| "lsof is empty, so nothing holds it" | Dissenting daemons, sibling snapshot mounts, and foreign namespaces are all invisible to lsof |
| Believing `losetup -d` / `umount` rc=0 | Both "succeed" while another namespace keeps the device busy — confirm with `losetup -a` / `lsblk` |
| Running `fuser` on a path after unmounting it | It reports on whatever mount now covers the path — run finders **before** detach attempts |
| `umount --lazy` as a fix | Hides the mount, releases nothing, and destroys the easy diagnosis path |
| Force-eject during a backup/copy | In-flight writes lost; filesystem structures can tear — stop the writer first |
