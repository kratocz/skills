#!/usr/bin/env bash
# Remove every linked git worktree of a repository. Branches are kept.
#
# A worktree is skipped when
#   - a process has its current directory inside it (Docker VM helpers excepted), or
#   - it holds work that exists nowhere else: uncommitted changes, untracked
#     files, or ignored files that are not regenerable (see REGENERABLE).
# An untracked or ignored file counts as saved when an identical copy exists
# at the same path in the main checkout or under $RESCUE/<worktree>/.
#
# Usage: cleanup-worktrees.sh [--yes] [repo-dir]     (dry run without --yes)
# Env:   RESCUE       rescue directory   (default: <main checkout>/.worktree-rescue)
#        REGENERABLE  extended regex of ignored paths that may be lost
#        IGNORE_PROCS extended regex of process names that do not count as users
set -u
DO=0; [ "${1:-}" = "--yes" ] && { DO=1; shift; }
REPO=$(git -C "${1:-.}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || { echo "FAIL: not a git repository"; exit 1; }
ROOT=$(git -C "$REPO/.." rev-parse --show-toplevel 2>/dev/null || dirname "$REPO")
RESCUE=${RESCUE:-$ROOT/.worktree-rescue}
REGENERABLE=${REGENERABLE:-'(^|/)(node_modules|\.venv|venv|__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|htmlcov|\.terraform|\.gradle|\.next|dist|build|target|[^/]*\.egg-info)(/|$)|(^|/)(\.DS_Store|\.coverage[^/]*|junit\.xml|coverage\.xml|[^/]*\.tfplan|tfplan)$'}
IGNORE_PROCS=${IGNORE_PROCS:-'^(OrbStack|com\.docker|Docker)'}
cd "$ROOT" || exit 1

# cwd of every process: "<command>\t<dir>"
if command -v lsof >/dev/null; then
  cwds=$(lsof +c 0 -d cwd -Fcn 2>/dev/null | awk '/^c/{c=substr($0,2)} /^n/{print c "\t" substr($0,2)}')
else
  cwds=$(for p in /proc/[0-9]*; do d=$(readlink "$p/cwd" 2>/dev/null) && printf '%s\t%s\n' "$(cat "$p/comm" 2>/dev/null)" "$d"; done)
fi
busy() { printf '%s\n' "$cwds" | awk -F'\t' -v w="$1" -v ig="$IGNORE_PROCS" '($2==w || index($2, w "/")==1) && $1 !~ ig {f=1} END{exit !f}'; }
saved() { cmp -s "$1/$2" "$ROOT/$2" || cmp -s "$1/$2" "$RESCUE/$3/$2"; }

unsaved_in() {  # $1 worktree path, $2 name
  git -C "$1" status --porcelain --untracked-files=all | while IFS= read -r line; do
    f=${line:3}
    [ "${line:0:2}" = "??" ] && saved "$1" "$f" "$2" && continue
    echo "$line"
  done
  git -C "$1" ls-files --others --ignored --exclude-standard --directory | command grep -Ev "$REGENERABLE" |
  while IFS= read -r e; do
    # "./" keeps a name starting with "-" from being read as a find option
    if [ -d "$1/$e" ]; then (cd "$1" && find "./${e%/}" -type f | sed 's|^\./||') | command grep -Ev "$REGENERABLE"; else echo "$e"; fi
  done | while IFS= read -r f; do saved "$1" "$f" "$2" || echo "!! $f"; done
}

list=$(git worktree list --porcelain | sed -n 's/^worktree //p' | tail -n +2)
total_kb() { printf '%s\n' "$list" | while IFS= read -r w; do [ -d "$w" ] && du -sk "$w" 2>/dev/null; done | awk '{s+=$1} END{print s+0}'; }
before=$(total_kb)
removed=0; skipped=0
while IFS= read -r wt; do
  [ -n "$wt" ] || continue
  n=${wt##*/}
  if [ ! -d "$wt" ]; then echo "stale $n: directory gone, pruned at the end"; continue; fi
  if busy "$wt"; then echo "SKIP $n: a running process is inside"; skipped=$((skipped+1)); continue; fi
  u=$(unsaved_in "$wt" "$n")
  if [ -n "$u" ]; then echo "SKIP $n: unsaved work:"; echo "$u" | sed 's/^/       /'; skipped=$((skipped+1)); continue; fi
  if [ $DO = 1 ]; then
    git worktree remove --force --force "$wt" && { echo "removed $n"; removed=$((removed+1)); }
  else
    echo "would remove $n"; removed=$((removed+1))
  fi
done <<< "$list"

if [ $DO = 1 ]; then
  git worktree prune
  after=$(total_kb)
  echo "freed $(( (before-after)/1024 )) MB"
  [ $skipped = 0 ] && echo "OK: removed $removed worktrees" || echo "FAIL: removed $removed, skipped $skipped (see SKIP lines)"
else
  echo "DRY RUN: would remove $removed, skip $skipped; run with --yes to delete"
fi
