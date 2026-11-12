# Weekly-High-Frequency-EWS-risk-alerts

Indian HF early-warning (EWS) risk alerts pipeline.

## Data layout

| Location | Purpose |
| --- | --- |
| `INDEX_DATA_DIR` (default: `.data/index-data`) | Clone of `samviduday-code/index-data` with fetch/build scripts |
| `New/external_hf/latest.json` | Built EWS vintages consumed by the digest |
| `.ews/slack_last_post.json` | Repeat guard (not committed) |

Bootstrap index-data:

```bash
bash scripts/bootstrap_index_data.sh
```

## Weekly Monday digest

```bash
.venv/bin/python -m ews weekly              # stdout only
.venv/bin/python -m ews weekly --post-slack  # requires SLACK_BOT_TOKEN
```

Gates: refuse when monthly data is older than 75 days; skip duplicate digests in the same ISO week; High_Priority flags only.

Delivery channel: `#weekly-high-frequency-ews` (`C0CH2MP70RF`).

## Development (Cloud Agent)

```bash
bash .cursor/install.sh
.venv/bin/python -m ews status
.venv/bin/pytest -q
```
