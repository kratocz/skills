---
name: setup-tracker
description: Configure the session-tracker plugin. Use when the user wants to set up time tracking, configure Toggl or Clockify, run initial setup, says "/setup-tracker", or when start-session fails because config is missing.
version: 1.6.0
allowed-tools: Read, Write, Bash
---

# Setup Tracker

Configure session-tracker to connect to a time tracking service.

## Steps

1. Ask the user which backend they want to use: **Toggl Track** or **Clockify**.

2. Ask for their API key:
   - **Toggl**: Profile page → API token (bottom of page at https://track.toggl.com/profile)
   - **Clockify**: Settings → API Keys (at https://app.clockify.me/user/settings)

3. Verify the API key by fetching workspaces:

   **Toggl:**
   ```bash
   KEY=<api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     https://api.track.toggl.com/api/v9/workspaces
   ```
   (The stdin `--config` trick keeps the key out of argv and sidesteps sandboxes that rewrite colon-bearing arguments like `-u user:token` into file paths.)

   **Clockify:**
   ```bash
   curl -s -H "X-Api-Key: <api_key>" https://api.clockify.me/api/v1/workspaces
   ```

   If the request fails (HTTP error or empty array), tell the user the API key is invalid and ask again.

4. If multiple workspaces are returned, list them and ask the user to choose one.

5. Ask whether time entries should be marked as **billable** ([Y/n], default `yes`). Store as `billable: true` or `false` at the top level of the config.

6. Ask for the preferred **language code** (default `en`). Common codes: `en`, `cs`, `de`, `fr`, `es` — accept any ISO 639-1 / BCP-47 code. This language is used for Claude-generated text (prompts, confirmations, descriptions derived from a URL title). Store as `language: "<code>"` at the top level of the config.

7. (Optional) Ask if the user wants a default project. If yes, fetch projects for the selected workspace and let them choose. If no, `default_project_id` will be `null`.

   **Toggl projects:**
   ```bash
   KEY=<api_key read into a shell variable, not echoed>
   printf 'user = "%s:api_token"\n' "$KEY" | curl -s --config - \
     "https://api.track.toggl.com/api/v9/workspaces/<workspace_id>/projects?active=true"
   ```

   **Clockify projects:**
   ```bash
   curl -s -H "X-Api-Key: <api_key>" "https://api.clockify.me/api/v1/workspaces/<workspace_id>/projects"
   ```

8. Create the config directory and write `~/.claude/plugins/session-tracker/config.json`:

   ```bash
   mkdir -p ~/.claude/plugins/session-tracker
   ```

   Then use the Write tool to write the config file:

   **Toggl:**
   ```json
   {
     "backend": "toggl",
     "billable": <true or false>,
     "language": "<code>",
     "toggl": {
       "api_key": "<api_key>",
       "workspace_id": <workspace_id>,
       "default_project_id": <project_id or null>
     }
   }
   ```

   **Clockify:**
   ```json
   {
     "backend": "clockify",
     "billable": <true or false>,
     "language": "<code>",
     "clockify": {
       "api_key": "<api_key>",
       "workspace_id": "<workspace_id>",
       "default_project_id": "<project_id or null>"
     }
   }
   ```

9. Confirm completion in the configured language (default English): "Setup complete. Use /start to begin tracking."
