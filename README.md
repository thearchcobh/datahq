# The Arch Data HQ

Central ingestion and analytics repository for The Arch.

The first version is designed to sync operational data from Square and Revolut Business into Supabase/Postgres, then support reporting and analysis on top of that data.

## Architecture

```text
Square API ────┐
               ├─> Python ingestion ─> GitHub Actions ─> Supabase/Postgres
Revolut API ───┘
```

## Current structure

- `src/datahq/database.py` — Supabase connection, sync state and audit helpers
- `src/datahq/square.py` — stable entry point for the existing Square Python logic
- `src/datahq/revolut.py` — entry point for Revolut Business ingestion
- `src/datahq/main.py` — command-line runner
- `.github/workflows/sync-data.yml` — manual and 15-minute scheduled sync
- `supabase/migrations/` — database schema tracked in source control

## GitHub Actions secrets

The scheduled workflow expects these repository secrets:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SQUARE_ACCESS_TOKEN`
- `SQUARE_LOCATION_ID`
- `REVOLUT_CLIENT_ID`
- `REVOLUT_PRIVATE_KEY`
- `REVOLUT_REFRESH_TOKEN`

Never commit real credentials. `.env.example` contains names only.

For the backend Supabase credential, use a server-side secret key (`sb_secret_...`) or service-role key. Do not expose it in frontend code.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
cp .env.example .env
python -m datahq.main square
```

## Next steps

1. Move the existing local Square API code into `src/datahq/square.py` (or split it into source-specific modules while preserving `sync_square()`).
2. Add the Supabase and Square secrets to GitHub Actions.
3. Test Square ingestion manually using **Actions → Sync operational data → Run workflow**.
4. Configure Revolut Business API read credentials and implement the Revolut sync.
5. Add reporting views once real data is landing reliably.
