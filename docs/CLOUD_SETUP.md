# Cloud setup and deployment

This project deploys as a Python command-line tool. It does not need a web
server, listening port, or background service.

## Install

Use Python 3.10 or newer (validated with Python 3.12). In the existing cloud
checkout, run:

```bash
cd /workspace/Neil-agents
./scripts/setup-cloud.sh
source /workspace/.venvs/neil-agents/bin/activate
outreach --help
```

The script installs the CLI and its dependencies in an isolated virtual
environment, checks dependency compatibility, and runs a drafting dry run.
It copies example contacts and sender background only if the local files do
not exist. Repeated setup preserves those files and existing credentials.
To use another virtual environment location, set `OUTREACH_VENV_DIR` before
running the script and activate that location instead.

Dependencies have version ranges and no lockfile, so a fresh installation
may resolve newer compatible releases.

## Run safely

Customize the ignored `contacts.csv` and `me.md` files, then preview:

```bash
outreach draft --limit 5 --dry-run
```

This reads the input files without making API calls or writing `drafts.csv`.
Activate the virtual environment again in each new shell. Use the existing
isolated checkout; do not create a Git worktree unless explicitly requested.

## Enable live generation

Supply `ANTHROPIC_API_KEY` securely through cloud environment settings, or
in a local ignored `.env` file as described in the README. Allow HTTPS access
to `api.anthropic.com`. Never commit credential values.

Once configured, this command makes paid API calls and writes local drafts:

```bash
outreach draft --limit 5
```

## Enable Gmail export

Follow the README to enable the Gmail API and download a Desktop OAuth client
as ignored `credentials.json` in the repository root. Authorization creates
ignored `token.json`. Required Google HTTPS destinations are:

- `accounts.google.com`
- `oauth2.googleapis.com`
- `www.googleapis.com`
- `gmail.googleapis.com`

The CLI uses a browser and localhost callback for its first OAuth sign-in.
That interactive flow has not been validated in the cloud environment.
It needs a usable browser/callback path or an existing valid authorized token.

Review `drafts.csv` and mark the intended rows `approved`, then preview:

```bash
outreach export --dry-run
```

Only after reviewing the preview, run `outreach export` to create real Gmail
drafts. This changes approved rows to `exported` to prevent repeat export.

## Validation and publication

Cloud onboarding verified:

- Editable installation and repeat installation completed successfully.
- Dependency compatibility checks and Anthropic/Google SDK imports passed.
- Draft dry run read an example contact and skipped API calls.
- Export dry run selected only approved rows and preserved the input CSV.
- Application source and dependency declarations were unchanged.

There is no existing automated test suite. Live Anthropic generation and Gmail
export were not tested because credentials were absent.

The cloud configuration draft separately contains installation/startup
instructions, an Anthropic credential requirement, and network destinations.
GitHub stores this documentation and setup script; pushing them does not
publish the cloud environment or supply credentials. Review and save the
configuration in environment settings, then publish it to retain the prepared
filesystem snapshot. Processes and shell activation do not survive publication.
Do not commit `.env`, OAuth files, contact lists, or generated drafts.
