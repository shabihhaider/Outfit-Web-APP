# Environment Setup Profiles

This repository supports two professional local backend profiles:

1. Local MySQL profile (safer for offline and isolated development)
2. Supabase staging profile (mirrors production engine with isolated data)

## Files

- .env.local-mysql.example
- .env.local-supabase-staging.example

## Recommended Workflow

1. Copy one profile to `.env` in the repository root.
2. Update secrets and DB credentials.
3. Run migrations.
4. Start backend and frontend.

## Commands

1. `Copy-Item .env.local-mysql.example .env`
2. or `Copy-Item .env.local-supabase-staging.example .env`
3. `set FLASK_APP=run.py`
4. `set FLASK_CONFIG=development`
5. `flask db upgrade`
6. `python run.py`

## Profile Selection Rules

- `USE_LOCAL_MYSQL=1` forces local MySQL and ignores `DATABASE_URL`.
- `USE_LOCAL_MYSQL=0` (or unset) allows `DATABASE_URL` to be used.

## Production Safety

- Never point local development to production Supabase.
- Keep production secrets only in deployment environment variables/secrets manager.
