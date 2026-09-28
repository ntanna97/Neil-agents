"""outreach: draft personalized LinkedIn notes and emails, then push approved ones to Gmail drafts."""
import argparse
import base64
import csv
import json
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
MODEL = "claude-sonnet-4-6"
CONTACT_FIELDS = ["name", "linkedin_url", "company", "title", "mit_program",
                  "grad_year", "past_employers", "notes", "target_role"]
DRAFT_FIELDS = ["hook_used", "linkedin_note", "email_subject", "email_version", "status"]
NOTE_LIMIT = 280
MAX_ATTEMPTS = 3
SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "linkedin_note": {"type": "string"},
        "email_subject": {"type": "string"},
        "email_body": {"type": "string"},
    },
    "required": ["hook", "linkedin_note", "email_subject", "email_body"],
    "additionalProperties": False,
}
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_message(contact, me):
    facts = {k: (contact.get(k) or "").strip() for k in CONTACT_FIELDS}
    return (f"SENDER BACKGROUND:\n{me.strip()}\n\n"
            f"CONTACT:\n{json.dumps(facts, indent=2)}")


def problems(d):
    """Return rule violations the model can be asked to fix; empty list means OK."""
    if d["hook"].strip() == "NO_HOOK":
        return []
    out = []
    if len(d["linkedin_note"]) > NOTE_LIMIT:
        out.append(f"linkedin_note is {len(d['linkedin_note'])} characters; the limit is {NOTE_LIMIT}.")
    if any("!" in d[k] for k in ("linkedin_note", "email_subject", "email_body")):
        out.append("Remove every exclamation mark.")
    words = len(d["email_body"].split())
    if not 60 <= words <= 95:
        out.append(f"email_body is {words} words; aim for about 75.")
    return out


def generate(client, system, contact, me):
    messages = [{"role": "user", "content": build_message(contact, me)}]
    for attempt in range(MAX_ATTEMPTS):
        resp = client.messages.create(
            model=MODEL, max_tokens=2000, system=system, messages=messages,
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        text = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(text)
        issues = problems(data)
        if not issues:
            return data, []
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "Fix these issues and return the full JSON again:\n- "
                      + "\n- ".join(issues)}]
    return data, issues


def cmd_draft(args):
    load_dotenv(HERE / ".env")
    system = (HERE / "prompt.txt").read_text(encoding="utf-8")
    me = Path(args.me).read_text(encoding="utf-8")
    contacts = read_csv(args.contacts)
    missing = [f for f in CONTACT_FIELDS if contacts and f not in contacts[0]]
    if missing:
        sys.exit(f"{args.contacts} is missing columns: {', '.join(missing)}")

    # Keep existing drafts (and any approvals) so reruns only process new contacts.
    existing = read_csv(args.out) if Path(args.out).exists() else []
    done = {r["linkedin_url"] for r in existing}
    todo = [c for c in contacts if c["linkedin_url"] not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    print(f"{len(todo)} contact(s) to draft ({len(done)} already in {args.out}).")

    if args.dry_run:
        for c in todo:
            print(f"\n=== {c['name']} ===\n{build_message(c, me)}")
        print(f"\n[dry run] {len(todo)} API call(s) skipped; {args.out} not written.")
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set. Add it to .env (see .env.example).")
    import anthropic
    client = anthropic.Anthropic()
    extra = [k for k in contacts[0] if k not in CONTACT_FIELDS + DRAFT_FIELDS] if contacts else []
    fields = CONTACT_FIELDS + extra + DRAFT_FIELDS
    rows = existing
    for i, c in enumerate(todo, 1):
        try:
            d, issues = generate(client, system, c, me)
        except anthropic.APIError as e:
            print(f"[{i}/{len(todo)}] {c['name']}: API error, skipped ({e})")
            continue
        no_hook = d["hook"].strip() == "NO_HOOK"
        rows.append({**c,
                     "hook_used": "" if no_hook else d["hook"],
                     "linkedin_note": "" if no_hook else d["linkedin_note"],
                     "email_subject": "" if no_hook else d["email_subject"],
                     "email_version": "" if no_hook else d["email_body"],
                     "status": "no_hook" if no_hook else "drafted"})
        write_csv(args.out, rows, fields)  # save after every row so a crash loses nothing
        note = f" WARNING: {' '.join(issues)}" if issues else ""
        print(f"[{i}/{len(todo)}] {c['name']}: {rows[-1]['status']}{note}")
    print(f"Wrote {args.out}. Set status to 'approved' on rows to send, then run: outreach export")


def gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    token, secrets = HERE / "token.json", HERE / "credentials.json"
    creds = Credentials.from_authorized_user_file(str(token), GMAIL_SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secrets.exists():
                sys.exit("credentials.json not found. Download an OAuth client (Desktop app) from Google Cloud.")
            creds = InstalledAppFlow.from_client_secrets_file(str(secrets), GMAIL_SCOPES).run_local_server(port=0)
        token.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def cmd_export(args):
    rows = read_csv(args.drafts)
    approved = [r for r in rows if r.get("status", "").strip().lower() == "approved"]
    if args.limit is not None:
        approved = approved[:args.limit]
    print(f"{len(approved)} approved row(s) to export.")
    if args.dry_run:
        for r in approved:
            print(f"\n=== To: {r.get('email') or '(no email column)'} | {r['email_subject']} ===\n{r['email_version']}")
        return
    if not approved:
        return
    svc = gmail_service()
    for r in approved:
        msg = MIMEText(r["email_version"])
        msg["to"] = r.get("email", "")
        msg["subject"] = r["email_subject"]
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        r["status"] = "exported"  # prevents duplicate drafts on the next run
        write_csv(args.drafts, rows, list(rows[0].keys()))
        print(f"Gmail draft created: {r['name']}")


def main():
    p = argparse.ArgumentParser(prog="outreach", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="generate drafts.csv from contacts.csv and me.md")
    d.add_argument("--contacts", default="contacts.csv")
    d.add_argument("--me", default="me.md")
    d.add_argument("--out", default="drafts.csv")
    e = sub.add_parser("export", help="create Gmail drafts for rows with status 'approved'")
    e.add_argument("--drafts", default="drafts.csv")
    for s in (d, e):
        s.add_argument("--limit", type=int, metavar="N", help="process at most N rows")
        s.add_argument("--dry-run", action="store_true", help="show what would happen without calling APIs")
    args = p.parse_args()
    cmd_draft(args) if args.cmd == "draft" else cmd_export(args)


if __name__ == "__main__":
    main()
