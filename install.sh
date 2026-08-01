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

# Prune broken symlinks left over from previous layouts
for d in "$HOME/.agents/skills" "$HOME/.claude/skills" \
         "$HOME/.gemini/antigravity-cli/skills"; do
  [ -d "$d" ] || continue
  for l in "$d"/*; do
    if [ -L "$l" ] && [ ! -e "$l" ]; then rm "$l"; echo "pruned: $l"; fi
  done
done

echo "Done."
