---
name: second-opinion
description: Get a second opinion from Gemini and/or GPT on the current topic
argument-hint: [--gemini|--gpt] [question]
allowed-tools: [Bash]
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

3. Pass the prompt via stdin to the CLI tools:
   - Gemini: `echo "$PROMPT" | gemini`
   - GPT/Codex: `echo "$PROMPT" | codex`

   Prerequisites: `gemini` and `codex` must be installed and configured by the user (auth, API keys, subscription — the plugin does not handle this).

4. Display responses clearly labeled:
   - `## Gemini` section
   - `## GPT (Codex)` section

5. Optionally note key differences or agreements between the responses.
