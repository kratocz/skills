---
name: gmail-compose
description: Write, draft and send e-mail through the Gmail MCP connector without Gmail mangling the links — every bare domain in plain text gets linkified and its visible text replaced by a google.com/url redirect, in the copy that is actually sent. Covers the mandatory draft → approval → send → verify loop, generating `htmlBody` from the approved Markdown with a bundled script, replacing a reply draft without detaching it from its thread, and attachments with inline images. Use ALWAYS before calling the Gmail connector's reply, send_message, create_draft or update_draft — when the user says "odpověz na ten mail" or "reply to this email" for a Gmail mailbox, "napiš draft", "pošli jí to", "draft a reply", "send it to her". An IMAP mailbox served by zerolib-email is `mail-catchup`; a chat or direct message is `dm-compose`.
license: MIT
---

# Gmail Compose

Draft, send and verify e-mail through the Gmail MCP connector. The skill exists because of one trap that silently looks like success: a message passed as plain text has every domain-shaped token linkified on the way out, and the damage is stored in the sent message where nothing can take it back.

The tool names below are the connector's own (`reply`, `send_message`, `create_draft`, `update_draft`, `get_message`, `get_thread`, `list_drafts`, `delete_draft`); a harness may prefix them, e.g. `mcp__claude_ai_Gmail__reply` in Claude Code.

## The trap: bare domains in plain text are destroyed

**Verified 2026-08-17 on a message actually sent.** When `reply` (or `send_message`) is called **with only `body`** (plain text), the tool converts the text to HTML itself, linkifies every token of the form `name.tld` and **replaces the visible text** of the link as well.

The sentence

```
The site example.com is run by Example.ORG.
```

arrives in the sent message as

```
The site https://www.google.com/url?q=http://example.com&source=gmail&ust=…&sa=E is run by
https://www.google.com/url?q=http://Example.ORG&source=gmail&ust=…&sa=E.
```

This is not a rendering artefact on the recipient's side: it is stored in the sent message and cannot be recalled. The e-mail looks amateurish, which hurts most in client communication.

**At risk:** anything shaped `something.tld` with a real TLD, including company names that merely look like a domain (`Example.CZ`). **Safe:** `sitemap.xml`, `index.php`, any token without a dot — `.xml` and `.php` are not TLDs.

## Rule: always send `htmlBody`

Never send `body` alone. Always build `htmlBody` and leave plain text, at most, as the alternative part. The conversion, and with it the linkification, is then yours and not the tool's.

**A domain that must NOT be a link** (a company name, a mention in prose) is broken with a span — invisible to the reader, no longer one contiguous token to the linkifier:

```html
The site example<span>.</span>com is run by Example<span>.</span>ORG
```

**The span protects the visible text, not the `href` (verified 2026-08-25 on a sent message).** Even with an honest anchor in `htmlBody`, Gmail **rewrites the `href` on send** to `https://www.google.com/url?q=…&source=gmail&ust=…&sa=E`. The visible text stays intact, which is what matters, because the e-mail does not look broken. But the plain-text alternative that Gmail generates prints that long address on a separate line below the signature, visible in a client without HTML.

The `href` wrapping cannot be prevented, only survived with clean text. When a domain in the signature is **information, not a link**, it is cleaner not to make it a link at all (`web: example<span>.</span>com`) — then Gmail has nothing to wrap and the plain-text alternative stays clean too.

**A domain that MUST be a link** is written as an honest anchor with a short text label:

```html
Details are on <a href="https://www.example.com/">their website</a>.
```

Never leave a bare URL as the link text; that is exactly what Gmail rewrites.

**Side effect of the span (verified 2026-08-18):** in the generated plain-text alternative Gmail may break the line exactly at the span boundary — `robots` at the end of one line and `.txt` at the start of the next. HTML renders correctly, so this is cosmetic in clients without HTML. Not worth fixing, but keep it in mind for a token in a prominent place (signature, product name).

## Steps

1. **Draft into a file, not straight into Gmail.** Write the text to a `.md` file in the session's scratch directory so it can be iterated paragraph by paragraph and the user sees all of it.
2. **Get approval.** Sending is irreversible and goes out to a specific person. Never send without an explicit "send" (in Czech: „pošli“).
3. **Send with `htmlBody`** generated from the approved file (see *Converting the approved text* below). For a reply in a thread use `reply` with the `messageId` of the thread's last message; for a draft use `create_draft` with `replyToMessageId`.
4. **Verify what actually went out.** Right after sending:

   ```
   get_message(messageId=<returned id>, messageFormat=FULL_CONTENT)
   ```

   and check that its `htmlBody` does **not** contain `google.com/url?q=` in the visible text. Never skip this step: it is the only place the mistake can be caught before the recipient sees it.

   **When the user sent the draft by hand**, there is no returned id: call `get_thread(threadId, messageFormat=MINIMAL)`, take the last message labelled `SENT`, and only then `get_message(FULL_CONTENT)` on it — `FULL_CONTENT` over the whole thread would pull in every quoted message too. Check only your own text above the quote; the quoted original carries its own `<a href>` and that is not your error.

   **Verify a draft right after creating it** with `list_drafts` and `view: DRAFT_VIEW_FULL` (e.g. with `query: "subject:<word from the subject>"`): it returns `sender`, `toRecipients`, `ccRecipients`, `subject` and the full `htmlBody`, so sender, recipients and text can be compared with the approved file. Verified 2026-11-16. The default `list_drafts` without `view` returns only metadata, and `get_thread` does not return drafts. This does not verify attachments, so for a draft with attachments ask the user to check them in Gmail.

## Replacing a reply draft: `update_draft` detaches the thread

`update_draft` rewrites the text but **detaches the draft from its thread** — it loses In-Reply-To and the draft's `threadId` becomes its own `messageId` (verified 2026-08-20). For a standalone message `update_draft` is fine; for a reply in a thread do this instead:

1. Create a new draft with `create_draft` and `replyToMessageId`, and confirm in the response that the returned `threadId` is the original thread's id.
2. Delete the old draft with `delete_draft(draftId)` (in some harnesses a deferred tool that has to be loaded first), but only on an explicit "delete" from the user: deleting a draft cannot be undone. Before deleting, confirm with `list_drafts` that the id belongs to the draft you are talking about (recipient, date). Verified 2026-11-15/16 on five drafts.
3. Tell the user which draft is current and which is waiting to be deleted.

Threading can also be checked through `list_drafts`, which returns each draft's `threadId`.

## Attachments and inline images

Verified 2026-11-13 on a draft with one inline screenshot and four PDFs:

- **Pass an attachment as a file reference** of the form `sha256:<hex>:<absolute path>`. The tool accepts it only for a file inside the session's working directory or its scratch directory and rejects a path elsewhere (such as `~/Documents`). Copy the files into `<scratch>/attach/` first and compute the hash from the copy (`shasum -a 256`).
- **An inline image** is an attachment with `inline: true`, referenced from the HTML as `cid:att<N>`, where `N` is its position in the attachment list counted from zero. Put the image first and write `<img src="cid:att0">` in the text.
- **`update_draft` drops attachments.** For every text change to a draft with attachments, create a new draft with `create_draft` carrying all the attachments again, and delete the old one once the user agrees (see above). Note the new draft's id wherever the state of the letter is kept.
- **Create a draft with attachments only after an explicit "done".** Iterate over the `.md` until then. On 2026-11-15 four versions of one draft were created within an hour because the user kept editing the text, and each cost a new draft plus deleting the old one.
- **Reading the draft back** (`DRAFT_VIEW_FULL`, step 4 above) verifies the text, not the attachments. Ask the user to check the image and the attachments in Gmail.

## Converting the approved text to `htmlBody`

Do not write `htmlBody` by hand; generate it from the approved `.md` with `scripts/md2html.py` in this skill's directory:

```bash
python3 -I <skill-dir>/scripts/md2html.py <letter.md> --section "## Email text" -o <scratch>/email.html
```

The section heading is whatever heading the draft file uses above the e-mail text; without `--section` the whole file is taken. A leading `**Subject:** …` line (or the Czech `**Předmět:** …`) is dropped, since the subject goes to the tool's `subject` parameter. Paragraphs become `<p>`, lines inside one paragraph (a signature) are joined with `<br>`, a `### ` heading becomes a bold paragraph, and numbered and bulleted lists, bold, italic and `[text](url)` links are supported. Every bare domain in the visible text is broken with a span. The script exits with an error when a domain survives in the visible text or when a link's text is itself a URL or a domain. Paste the output into `htmlBody` unchanged. For each new version of the letter, run the script again and `diff` the output against the previous one to see what changes in the draft. On 2026-11-16 the script produced, from the text of an e-mail already sent, HTML byte-identical to the hand-verified version. It runs on Python 3.9 and later.

## Formatting the text

- **Do not hard-wrap sentences.** A paragraph is one long line; the reader's client wraps it. In HTML every paragraph is a `<p>`, never `<br>` every 80 characters.
- **No guesses stated as facts.** Every "who did what" has to be traceable to a source you actually read. When the source is silent, phrase it without an actor or ask.
- **Write in the recipient's language.** In Czech, polite plural pronouns addressing the recipient are capitalised (`Vám`, `Vás`, `Váš`, `Vaše`) — the convention in letters and client communication. Check them before sending, but beware of false matches inside words (`vysvětlit`, `výsledek`). Czech quotation marks are `&bdquo;…&ldquo;`, the dash `&mdash;`.

## Checklist before sending

- [ ] Sending `htmlBody`, not just `body`?
- [ ] Every domain either broken with a span or an honest `<a>` with a text label?
- [ ] Paragraphs as `<p>`, no hard breaks in the middle of sentences?
- [ ] Polite pronouns capitalised where the language requires it?
- [ ] Draft verified with `list_drafts` and `DRAFT_VIEW_FULL` (sender, recipients, text)?
- [ ] An explicit "send" from the user?
- [ ] After sending: `get_message` and a check for `google.com/url?q=`?
