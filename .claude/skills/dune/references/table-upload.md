# Dune Table Upload & Management

Upload external data (CSV, NDJSON) to Dune as queryable tables.

## Endpoints (New — use these)

| Action | Method | URL |
|---|---|---|
| Create table | POST | `/v1/uploads` |
| Insert rows | POST | `/v1/uploads/:namespace/:table_name/insert` |
| Upload CSV | POST | `/v1/uploads/csv` |
| Clear table | POST | `/v1/uploads/:namespace/:table_name/clear` |
| Delete table | DELETE | `/v1/uploads/:namespace/:table_name` |
| List tables | GET | `/v1/uploads` |

Base URL: `https://api.dune.com/api`

All require header `X-DUNE-API-KEY`.

### Deprecated endpoints (removed March 1, 2026)

Old `/v1/table/*` paths map 1:1 to `/v1/uploads/*`. Request/response bodies unchanged.

## Create Table

```bash
curl -X POST https://api.dune.com/api/v1/table/create \
  -H 'X-DUNE-API-KEY: <key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "namespace": "my_user",
    "table_name": "interest_rates",
    "description": "10 year daily interest rates",
    "is_private": false,
    "schema": [
      {"name": "date", "type": "timestamp"},
      {"name": "dgs10", "type": "double", "nullable": true}
    ]
  }'
```

**Request body:**
- `table_name` (string, required) — must start with lowercase letter, alphanumeric + underscores only
- `schema` (array, required) — non-empty column definitions
- `namespace` (string, optional) — defaults to API key's namespace
- `is_private` (boolean, optional) — default false
- `description` (string, optional)

**Column schema:**
- `name` — must start with letter or underscore
- `type` — one of: `varchar`, `integer`, `double`, `boolean`, `int256`, `uint256`, `varbinary`, `timestamp`
- `nullable` — default true

**Response (200/201):**
```json
{
  "namespace": "my_user",
  "table_name": "interest_rates",
  "full_name": "dune.my_user.interest_rates",
  "example_query": "select * from dune.my_user.interest_rates",
  "already_existed": false
}
```

**Cost:** 10 credits per create. 409 if table already exists.

## Insert Rows

```bash
curl -X POST https://api.dune.com/api/v1/table/{namespace}/{table_name}/insert \
  -H 'X-DUNE-API-KEY: <key>' \
  -H 'Content-Type: text/csv' \
  --data-binary @data.csv
```

**Content types:**
- `text/csv` — comma-delimited, header row must match schema
- `application/x-ndjson` — one JSON object per line, keys match column names

**Limits:** max 1.2 GB per request. Atomic: all rows inserted or none.

**Response (200):**
```json
{"rows_written": 1000, "bytes_written": 45000}
```

**Cost:** 1 credit per insert request. 5-10 concurrent requests recommended max.

## Upload CSV (simple)

One-shot upload that auto-infers schema. Overwrites existing table if same name.

```python
from dune_client.client import DuneClient

dune = DuneClient()
with open("data.csv") as f:
    dune.upload_csv(
        data=f.read(),
        table_name="my_table",
        description="Description",
        is_private=False,
    )
```

```bash
curl -X POST https://api.dune.com/api/v1/table/upload/csv \
  -H 'X-DUNE-API-KEY: <key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "data": "col1,col2\nval1,val2\nval3,val4",
    "table_name": "my_table",
    "description": "Description",
    "is_private": false
  }'
```

**Limit:** < 200 MB. Overwrites existing data (no append).

Table accessible as: `dune.<namespace>.dataset_<table_name>`

## Clear & Delete

```bash
# Clear all rows, keep schema
curl -X POST https://api.dune.com/api/v1/table/{namespace}/{table_name}/clear \
  -H 'X-DUNE-API-KEY: <key>'

# Delete table entirely
curl -X DELETE https://api.dune.com/api/v1/table/{namespace}/{table_name} \
  -H 'X-DUNE-API-KEY: <key>'
```

## Recommended workflow for pipelines

1. **First run:** `create` table with explicit schema → `insert` CSV data
2. **Subsequent runs:** `clear` → `insert` (full refresh) or just `insert` (append)
3. **Simple one-off:** `upload/csv` (auto-schema, overwrites)

For our use case (daily DefiLlama snapshots): use `create` + `insert` with explicit schema so we control types and can append incrementally.
