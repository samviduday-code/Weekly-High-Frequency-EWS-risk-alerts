# Weekly-High-Frequency-EWS-risk-alerts

Indian HF early-warning (EWS) risk alerts pipeline.

## Development (Cloud Agent)

```bash
bash .cursor/install.sh
.venv/bin/python -m ews status
.venv/bin/pytest -q
```

## Weekly Monday run

Requires a checkout of `navi-corp/index-data` on `main` (set `INDEX_DATA_DIR` or grant repo access to the agent):

```bash
.venv/bin/python -m ews weekly --json
```

Optional: `INDEX_DATA_REPO`, `INDEX_DATA_GIT_URL`, `EWS_GIT_PUSH=0`.
