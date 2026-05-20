# Upload Workflow

Conventions for `{dashboard}/upload.py` — pushing CSVs to Dune.

## API Key

Read from local `.env` file in the dashboard directory, not from shell environment:

```python
def load_env():
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
```

## Table Schema

Define schemas explicitly in the script — never rely on auto-infer:

```python
TABLES = {
    "daily": {
        "table_name": "defi_overview_daily",
        "description": "...",
        "csv_file": "defi_overview_daily.csv",
        "schema": [
            {"name": "date", "type": "timestamp"},
            {"name": "tvl", "type": "double", "nullable": True},
            ...
        ],
    },
}
```

## CLI Flags

| Flag | Action |
|------|--------|
| `--table {key}` | Upload specific table only |
| `--clear` | Clear rows before insert (full refresh) |
| `--recreate` | Delete + create table (for schema changes) |
| `--dry-run` | Show what would happen |

## Credit Costs

| Operation | Credits |
|-----------|---------|
| Create table | 10 |
| Insert CSV | 1 |
| Clear table | 0 |
| Delete table | 0 |

## Workflow

```
First run:    create (10 cr) → insert (1 cr)
Daily refresh: clear (0 cr) → insert (1 cr)
Schema change: delete (0 cr) → create (10 cr) → insert (1 cr)
```

## Post-Upload: Refresh Matviews

After uploading new data, the matviews are stale. They still have the old data until refreshed.

- **CLI can't refresh matviews** — must be done in Dune UI (go to the matview query page and run it)
- **Always remind the user** to refresh matviews after an upload, especially after adding new entities (chains, tokens)
- **Dashboard queries will show stale/empty data** until matviews are refreshed — this is the #1 gotcha after an upload

## Common Issues

- **409 on create**: table already exists. Use `create` anyway — response includes `already_existed: true` and still returns namespace.
- **Schema change needed**: use `--recreate` (deletes then re-creates). Can't add/remove columns on existing table.
- **API key not found**: check `.env` file path. `load_env()` reads from `SCRIPT_DIR / ".env"`.
- **200 MB limit**: per-request CSV size limit. Split if needed.
- **Mostly empty dashboard after upload**: matview not refreshed. This is the most common issue — always refresh matviews after re-uploading data.

## API Reference

See the dune skill's [table-upload.md](../../dune/references/table-upload.md) for full endpoint docs.
