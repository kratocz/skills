---
name: mail-catchup
description: Catch up on an IMAP mailbox exposed through the zerolib-email MCP server (mcp-email-server) — list unread mail, read the relevant threads, summarize per thread what is asked of you and by when, recommend what to do, draft the reply into a dated file for approval, send it in-thread with a correctly encoded subject, and verify the copy in Sent before calling it sent. Use when the user says "/mail-catchup", "zkontroluj mi nové maily", "co mi přišlo do schránky", "check my mailbox", "catch up on email", or "odpověz na ten mail" for a mailbox served by mcp__zerolib-email__* tools. Gmail via the Gmail MCP is a different tool with different traps — that is gmail-compose.
argument-hint: "[account] [since-date]"
version: 1.0.0
license: MIT
---

# Mail Catch-up (IMAP via zerolib-email)

Read what arrived in an IMAP mailbox, turn it into a per-thread briefing with
the decisions it needs from the user, and — when a reply is wanted — take it
from a dated draft file through approval, sending and verification. The
sending half exists because the transport has a trap that silently looks
like success: a subject with non-ASCII characters crashes the server *before*
SMTP, and a return value of "sent" is not the same as a copy in Sent.

## Steps

### 1. Load the tools and pick the account

Load the deferred schemas in ONE batched call: `mcp__zerolib-email__list_available_accounts`,
`list_emails_metadata`, `get_emails_content`, `list_mailboxes`; add `send_email`
and `delete_emails` only when a reply is actually going out.

`list_available_accounts` → use an account with `can_receive=true`. If the
result is empty, the server is not configured — say so and stop; never ask
for credentials in chat.

### 2. List what is new

`list_emails_metadata(account, seen=false, page_size=50)` for the inbox. When
the user names a window ("od pondělí"), use `since` instead of, not in
addition to, `seen=false` — a mail read on the phone is still new to the
briefing.

Skip machine mail (Slack/GitHub/calendar notifications, confirmation codes)
in the briefing; mention it in one line at the end so the count adds up.

### 3. Read the relevant threads

`get_emails_content(account, email_ids=[…], mark_as_read=false)` — one call
for all ids; the default `mark_as_read=false` is the point: the briefing
must not flip flags the user relies on in their own client.

Group by thread using `in_reply_to` / `references` / `message_id`. Quoted
history inside a reply usually repeats the earlier mails verbatim — read the
newest mail of a thread fully and use the older ones only for what the quote
cut off (attachments, exact dates).

### 4. Brief per thread, newest thread first

For each thread: who wrote, when, what they want *from the user*, open
questions addressed to the user, any date they named. Then a one-line
"what this is waiting on".

Rules that come from the user's global instructions and cost real trust when
broken:

- **No inference stated as fact.** "Kdo co udělal / kdy / proč" must be in a
  mail you read. If the mail says "po interní diskuzi" without naming who
  decided, write it without an actor.
- **Deadlines: quote them or say there are none.** Check every mail in the
  thread for a date before writing "bez termínu"; the absence is itself a
  finding worth stating ("2. 7.: 'až bys měl čas' — výslovně bez tlaku").
- **Check Sent before assuming your side answered.** `list_emails_metadata(mailbox="Sent", since=<thread start>)`.
  An empty Sent over the thread's lifetime means the earlier draft never went
  out from this mailbox — a fact the user may not know and the briefing must
  surface.

Close with a recommendation (reply / call / delegate / ignore), not a menu.

### 5. Draft the reply into a file

Only when the user asks for a reply. Write it to
`docs/agent/email-draft-<YYYY-MM-DD>-<slug>.md` in the project (or the
scratchpad if the project has no such convention), with:

- metadata as a bullet list: `- **Datum přípravy:**`, `- **Vlákno:**` with
  the Message-ID being answered and its inbox id, `- **Status:** draft ke
  schválení, neodesláno`;
- sections **Příjemci** (To / Cc), **Předmět**, **Tělo** (in a code block,
  exactly as it will be sent), **Poznámky k draftu** (tone, what was left
  out and why, what is unverified).

Drafting rules:

- **Reply to whoever wrote to you, not to the whole thread**, unless told
  otherwise. A PM who forwarded a client thread to you alone expects an
  answer to himself; he rephrases for the client.
- **Mirror the other side's register** — tykání/vykání, salutation, sign-off.
- **Continuous paragraphs, no hard wrap** — the recipient's client reflows.
- **Dates carry a weekday only after `cal`** — run `cal <month> <year>`
  before writing "do středy 3. 9."; a wrong weekday in a commitment to a
  client is the cheapest mistake to avoid and the most embarrassing to make.
- **Commitments at the granularity you can keep.** After a long silence,
  "ještě tento týden" beats "do čtvrtka" that slips; and ask the recipient
  whether that granularity is enough for them.

Show the draft verbatim and stop. Nothing is sent without an explicit
"pošli" / "odešli".

### 6. Send in-thread with an encoded subject

Compose the call from the file, not from memory:

- `recipients` = only the approved To; `cc` only if approved.
- `in_reply_to` = Message-ID of the mail being answered; `references` = the
  thread's References chain plus that Message-ID, space-separated.
- `body` = the Tělo block verbatim (UTF-8 body is fine).
- **`subject` must be pre-encoded as an RFC 2047 encoded-word when it
  contains any non-ASCII character:**

  ```bash
  python3 -c 'import base64,sys; s=sys.argv[1]; print("=?utf-8?b?"+base64.b64encode(s.encode()).decode()+"?=")' "Re: GEO články - recenze"
  ```

  Why: mcp-email-server (verified on 1.5.2 under Python 3.12) sets
  `msg["Subject"] = str(Header(subject, "utf-8"))`, which stores the raw
  unicode string, and then fails in `as_bytes(policy=SMTP)` with
  `'ascii' codec can't encode character … in position N` — *before*
  `MAIL FROM`, so nothing leaves, and nothing lands in Sent. An ASCII
  encoded-word passes through untouched and the recipient's client decodes it.

First time a new pattern is used (encoded subject, attachment, new server
version): send the same shape to the user's own address first, read it back
with `list_emails_metadata` (the decoded subject shows there), then send the
real one. Delete the test from INBOX and Sent afterwards with `delete_emails`.

If the call raises instead of returning an outcome, do **not** retry blindly:
check Sent for a copy and reason from the error text which phase failed
before deciding a resend is safe. A duplicate to a client is worse than a
delay.

### 7. Verify, then record

- `list_emails_metadata(mailbox="Sent", since=<today>)` — the reply must be
  there with the decoded subject and the intended recipients. Only now say
  "odesláno".
- Rewrite the draft's `- **Status:**` line: sent when, to whom, via what,
  and any workaround used.
- Write into project memory what was promised (deliverables, dates), what
  questions were asked of the other side, and what the thread is now waiting
  on — this is the state the next catch-up starts from.

## Checklist before "odesláno"

- [ ] Only the approved recipients — nobody added "for context"?
- [ ] `in_reply_to` + `references` set, so it threads in Outlook?
- [ ] Subject with diacritics passed as `=?utf-8?b?…?=`?
- [ ] Weekdays in the text verified with `cal`?
- [ ] Copy visible in Sent?
- [ ] Draft file Status updated, promises written to memory?
