# Weekly-High-Frequency-EWS-risk-alerts

Indian HF early-warning (EWS) risk alerts pipeline.

## Data layout

| Location | Purpose |
| --- | --- |
| `data/New/external_hf/latest.json` | This week's vintage. Commit this file in the repo. |
| `data/New/external_hf/latest.example.json` | Shape to copy. The weekly command does not read it. |
| `.ews/email_last_post.json` | Repeat guard (not committed) |

Add this week's vintage on GitHub:

1. Open the repo, then **Add file → Create new file**.
2. Name the file `data/New/external_hf/latest.json` (type the slashes; GitHub creates the folders).
3. Paste the JSON. Start from `latest.example.json`. Set `monthly_as_of` to the real monthly date (`YYYY-MM-DD`, within 75 days). Each flag that should be emailed needs `"priority": "High_Priority"` and a `monthly_level` or `weekly_level` such as `"P1"`. `summary` is the line in the email. `id_prefix` is the indicator name.
4. Commit the file to `main`.

From a clone:

```bash
mkdir -p data/New/external_hf
# save the vintage as data/New/external_hf/latest.json
git add data/New/external_hf/latest.json
git commit -m "Add this week's EWS vintage"
git push
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
