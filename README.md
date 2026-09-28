# outreach

Drafts personalized LinkedIn connection notes and short emails from `contacts.csv` + `me.md`, then turns approved ones into Gmail drafts.

## Setup

```bash
pip install -e .            # installs the `outreach` command (or: pip install -r requirements.txt; python outreach.py ...)
cp .env.example .env        # add your ANTHROPIC_API_KEY
cp contacts.example.csv contacts.csv
cp me.example.md me.md
```

## Draft

```bash
outreach draft --limit 5 --dry-run   # print what would be sent, no API calls
outreach draft --limit 5             # write drafts.csv
```

`drafts.csv` = contact columns + `hook_used`, `linkedin_note`, `email_subject`, `email_version`, `status` (`drafted` / `no_hook`).
Rerunning only drafts contacts not already in `drafts.csv` (matched by `linkedin_url`), so your edits and approvals are kept.
Each draft is checked in code (note ≤280 chars, no `!`, email ~75 words); the model is asked to fix violations up to 2 more times, and a WARNING is printed if they remain.

Edit the system prompt in `prompt.txt`.

## Export to Gmail

1. In Google Cloud: enable the Gmail API, create an OAuth client ID (type "Desktop app"), download it as `credentials.json` into this folder.
2. In `drafts.csv`, set `status` to `approved` on rows you want. Add an `email` column (to contacts.csv or drafts.csv) to fill the To: field; otherwise drafts are created without a recipient.
3. Run:

```bash
outreach export --dry-run
outreach export
```

The first run opens a browser for Google sign-in and saves `token.json`. Exported rows are marked `exported` so they are never drafted twice.
