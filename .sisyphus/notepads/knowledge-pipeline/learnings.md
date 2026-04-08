# Knowledge Pipeline - Learnings

## Key Patterns Discovered

1. **RAGEngine.ingest_chunks() generates document_id via uuid5(NAMESPACE_URL, source)**
   - This means Document.id MUST use the same logic to maintain FK consistency
   - Solution: `doc_uuid = uuid.uuid5(uuid.NAMESPACE_URL, source_key)` when creating Document rows

2. **DB schema may be behind ORM models**
   - T24 metadata columns (doc_type, version, effective_date, expires_date, priority) were defined in models.py but not yet applied to the live database
   - Alembic migrations existed but hadn't been run; multiple heads with `down_revision = None`
   - Direct SQL ALTER TABLE was the safest approach

3. **Docker container is built from image, not volume-mounted**
   - Files uploaded via `scp` to `/opt/amazon-ai/` don't appear in the container
   - Must `docker cp` or rebuild image for changes to take effect
   - `scripts/` directory is not copied by Dockerfile (only `src/` and `alembic/`)
   - For CLI scripts: `docker cp` + `docker exec -w /app` works
   - For API changes: rebuild image required (`docker compose build app --no-cache`)

4. **PowerShell SSH escaping**
   - Complex Python one-liners fail with PowerShell string escaping
   - Solution: write scripts to files, scp to server, then execute

## Conventions

- `db_session()` is a contextmanager for non-FastAPI usage
- `get_db()` is the FastAPI Depends generator
- API routers use `APIRouter(prefix="/api/...", tags=[...])` pattern
- Auth: `Depends(get_current_user)` for JWT auth
- Document dedup key: `source` field (no content_hash column)
