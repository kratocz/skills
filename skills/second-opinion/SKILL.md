---
name: second-opinion
description: Get a second opinion from Gemini and/or GPT on the current topic
argument-hint: "[--gemini|--gpt] [question]"
allowed-tools: [Bash]
license: MIT
---
# Second Opinion

The user wants a second opinion from another AI model on an important topic, decision, or question.

## Usage
- `/second-opinion` — ask both Gemini and GPT based on the current conversation context
- `/second-opinion <question>` — ask both with an explicit question
- `/second-opinion --gemini` / `/second-opinion --gpt` — narrow to one model
- Flags and explicit question can be combined: `/second-opinion --gpt Which approach is safer?`

**Default is always ALL models.** The `--gemini`/`--gpt` flags narrow down only when explicitly requested.

## Instructions

1. Check if `--gemini` or `--gpt` flag is present in the arguments. Strip the flag; target ALL models if no flag.

2. **Build the prompt:**
   - If the user provided an explicit question (non-flag text): use that as the question.
   - If no question provided: infer the key topic or decision from the current conversation.
   - In both cases, include a concise summary of the relevant conversation context (max ~500 words) so the prompt is self-contained and understandable without the conversation history.
   - Frame the prompt clearly: summarized context first, then the specific question.

3. Ask the targeted models **concurrently** — the two calls are independent, so start both in one command and wait for both, instead of paying their latencies one after the other:
   - Gemini, through Antigravity CLI: `agy --mode plan --model <gemini-id> -p "$PROMPT"`. `-p` takes the prompt as its own value, so keep every other flag before it; `--mode plan` keeps the agent from editing files. Pick `<gemini-id>` at run time from `agy models`: the newest Gemini family at its highest effort. Never a `claude-*` id — Antigravity offers those too, and a second opinion from the model already answering is not one.
   - GPT, through Codex: `echo "$PROMPT" | codex exec --sandbox read-only --skip-git-repo-check -` (the trailing `-` reads the prompt from stdin). Plain `codex` is the interactive UI and exits with `stdin is not a terminal`.

   Write each answer and each stderr to its own file; show a tool's stderr only when it exits non-zero, since Codex streams its progress there. Verified 2026-10-31 with agy 1.2.14 and codex-cli 0.163.0. Gemini CLI, which this step used to call, was discontinued on 2026-06-18.

   Prerequisites: `agy` and `codex` must be installed and configured by the user (auth, API keys, subscription — the skill does not handle this).

4. Display responses clearly labeled:
   - `## Gemini` section
   - `## GPT (Codex)` section

5. Optionally note key differences or agreements between the responses.
