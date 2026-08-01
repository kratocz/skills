#!/bin/sh
# Live-development install: symlinks every skill from this working clone into
# agent skill directories, so edits made here are picked up without reinstall.
#
# For a one-shot install without a clone use the skills CLI instead:
#   npx skills add kratocz/skills
#
# Note for Claude Code: if you still have the skill plugins from
# kratocz/claude-plugins installed, uninstall them first — otherwise the same
# skills load twice (once as plugins, once from ~/.claude/skills).
set -eu

REPO=$(cd "$(dirname "$0")" && pwd -P)

link_all() {  # $1 = target directory
  mkdir -p "$1"
  for s in "$REPO"/skills/*/; do
    ln -sfn "${s%/}" "$1/$(basename "$s")"
  done
}

# Read by: Antigravity CLI, Codex, Copilot CLI, Gemini CLI, opencode
# (and Claude Code, with a delay)
link_all "$HOME/.agents/skills"

# Claude Code picks up changes in ~/.claude/skills instantly
link_all "$HOME/.claude/skills"

# Antigravity: kodex as an always-on rule (one-line pointer to the skill)
mkdir -p "$HOME/.gemini/antigravity-cli/rules"
ln -sfn "$REPO/rules/kodex.md" "$HOME/.gemini/antigravity-cli/rules/kodex.md"

# Prune broken symlinks left over from previous layouts of THIS repo only —
# links pointing anywhere else are never deleted, merely reported, because
# a broken target elsewhere may be temporary (renamed repo, unmounted disk)
# and the link itself records where it pointed.
OLD_REPO_HINT="antigravity-skills"   # former name of this repository
for d in "$HOME/.agents/skills" "$HOME/.claude/skills" \
         "$HOME/.gemini/antigravity-cli/skills"; do
  [ -d "$d" ] || continue
  for l in "$d"/*; do
    { [ -L "$l" ] && [ ! -e "$l" ]; } || continue
    target=$(readlink "$l")
    case "$target" in
      "$REPO"/*|*"/$OLD_REPO_HINT/"*)
        rm "$l" && echo "pruned: $l -> $target" ;;
      *)
        echo "note: broken symlink left untouched: $l -> $target" ;;
    esac
  done
done

echo "Done."
