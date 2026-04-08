# Knowledge Pipeline - Decisions

1. **Document ID generation**: Used `uuid.uuid5(uuid.NAMESPACE_URL, source_path)` to align with `ingest_chunks()` internal logic, ensuring FK consistency without modifying existing methods.

2. **Deduplication strategy**: Used `Document.source` field as the dedup key (no `content_hash` column in DB). With `--resume` flag, skip files whose source already exists in documents table.

3. **Schema migration**: Applied direct SQL ALTER TABLE instead of running alembic, because multiple migration heads existed with `down_revision = None`.

4. **API query endpoint**: Calls both `engine.answer()` for the LLM answer and `engine.search()` for source chunks, since `answer()` doesn't return chunk_text in its sources.
