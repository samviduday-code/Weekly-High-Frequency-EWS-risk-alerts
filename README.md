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

Slack delivery: set `SLACK_DM_CHANNEL_ID` (e.g. `D0C2GA3UR18`) on the automation.
The Cursor Slack MCP must be installed on the **same** Slack workspace as that channel
(`grid-go-navi` Enterprise Grid vs `navi-ofy2106` are separate installs).
