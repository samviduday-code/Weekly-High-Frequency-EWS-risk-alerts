# Weekly-High-Frequency-EWS-risk-alerts

Indian HF early-warning (EWS) risk alerts pipeline.

## Data layout

| Location | Purpose |
| --- | --- |
| `INDEX_DATA_DIR` (default: `.data/index-data`) | Clone of `samviduday-code/index-data` with fetch/build scripts |
| `New/external_hf/latest.json` | Built EWS vintages consumed by the digest |
| `.ews/email_last_post.json` | Repeat guard (not committed) |

Bootstrap index-data:

```bash
bash scripts/bootstrap_index_data.sh
```

## Weekly Monday digest

```bash
.venv/bin/python -m ews weekly              # stdout only
.venv/bin/python -m ews weekly --post-email  # requires SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD
```

Gates: refuse when monthly data is older than 75 days; skip duplicate digests in the same ISO week; High_Priority flags only.

Delivery: email to `samvid.uday@navi.com` (`EWS_EMAIL_TO` overrides the recipient). `SMTP_PORT` defaults to 587 with STARTTLS. Set `EWS_EMAIL_FROM` when the From address differs from `SMTP_USERNAME`.

## Development (Cloud Agent)

```bash
bash .cursor/install.sh
.venv/bin/python -m ews status
.venv/bin/pytest -q
```
