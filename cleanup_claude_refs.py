import os
import re

directory = '/Users/krato/IdeaProjects/github.com/kratocz/antigravity-skills'

replacements = {
    'AGENTS.md': 'AGENTS.md',
    '~/.gemini/antigravity-cli/data/': '~/.gemini/antigravity-cli/data/',
    '~/.gemini/antigravity-cli/projects/': '~/.gemini/antigravity-cli/projects/',
    '~/.gemini/antigravity-cli/settings.json': '~/.gemini/antigravity-cli/settings.json',
    'Antigravity': 'Antigravity',
    'Antigravity agent': 'Antigravity agent',
    'session-tracker-antigravity': 'session-tracker-antigravity',
    'mcp_': 'mcp_',
    'package.json (or other manifest)': 'package.json (or other manifest)',
    '${AGY_SKILL_DIR}': '${AGY_SKILL_DIR}'
}

def process_file(filepath):
    # Don't touch README.md as it might contain historical references we want to keep
    # Wait, README.md already got updated by me, but let's be careful.
    if os.path.basename(filepath) == 'README.md':
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for old, new in replacements.items():
        # Case sensitive replace except for 'Antigravity agent' which might be 'claude'
        new_content = new_content.replace(old, new)
        
    # Also replace lowercase 'claude' where it's used in paths or names (but carefully)
    # new_content = new_content.replace('~/.claude', '~/.gemini/antigravity-cli')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk(directory):
    if '.git' in root:
        continue
    for file in files:
        if file.endswith('.md') or file.endswith('.json') or file.endswith('.py'):
            process_file(os.path.join(root, file))

print("Cleanup done.")
