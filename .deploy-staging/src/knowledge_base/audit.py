"""Knowledge Base Quality Audit Pipeline.

Scans all existing documents for quality issues and submits findings
to the kb_review_queue for Boss review. Never auto-deletes.

Usage:
    python -m src.knowledge_base.audit
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class AuditFinding:
    """Single audit finding for a document/chunk."""
    document_id: str
    title: str
    issue_type: str  # "too_short", "duplicate", "no_embedding", "low_relevance"
    severity: str    # "warning", "critical"
    description: str
    chunk_index: Optional[int] = None


@dataclass
class AuditReport:
    """Summary of audit run."""
    total_documents: int = 0
    total_chunks: int = 0
    flagged_documents: int = 0
    findings: list[AuditFinding] = field(default_factory=list)
    quality_distribution: dict[str, int] = field(default_factory=dict)
    run_timestamp: str = ""

    def summary(self) -> str:
        """Generate human-readable audit summary."""
        lines = [
            "=== 知识库质量审计报告 ===",
            f"审计时间: {self.run_timestamp}",
            f"总文档数: {self.total_documents}",
            f"总分块数: {self.total_chunks}",
            f"问题文档数: {self.flagged_documents}",
            f"质量分布: {self.quality_distribution}",
            "",
            f"--- 发现的问题 ({len(self.findings)} 条) ---",
        ]
        for i, finding in enumerate(self.findings[:50], 1):  # Show first 50
            lines.append(
                f"  [{i}] [{finding.severity}] {finding.issue_type}: "
                f"{finding.title} - {finding.description}"
            )
        if len(self.findings) > 50:
            lines.append(f"  ... 还有 {len(self.findings) - 50} 条")
        return "\n".join(lines)


class KBAuditor:
    """Audits knowledge base quality without auto-deleting anything."""

    # Configurable thresholds
    MIN_CHUNK_LENGTH = 100  # chars — below this is "too short"
    DUPLICATE_SIMILARITY_THRESHOLD = 0.95  # cosine similarity

    def __init__(self, db: Session):
        self.db = db

    def audit_all(self) -> AuditReport:
        """Run full audit on all documents and chunks."""
        report = AuditReport(run_timestamp=datetime.now(timezone.utc).isoformat())

        # 1. Count totals
        report.total_documents = self._count_documents()
        report.total_chunks = self._count_chunks()

        # 2. Check for short content
        short_findings = self._check_short_content()
        report.findings.extend(short_findings)

        # 3. Check for missing embeddings
        no_embed_findings = self._check_missing_embeddings()
        report.findings.extend(no_embed_findings)

        # 4. Check for duplicates (cosine similarity)
        # NOTE: This is expensive for 550 docs. Use a sampling approach.
        dup_findings = self._check_duplicates()
        report.findings.extend(dup_findings)

        # 5. Compute quality distribution
        flagged_doc_ids = {f.document_id for f in report.findings}
        report.flagged_documents = len(flagged_doc_ids)

        critical_count = len([f for f in report.findings if f.severity == "critical"])
        warning_count = len([f for f in report.findings if f.severity == "warning"])
        report.quality_distribution = {
            "good": max(0, report.total_documents - report.flagged_documents),
            "warning": warning_count,
            "critical": critical_count,
        }

        return report

    def _count_documents(self) -> int:
        result = self.db.execute(text("SELECT COUNT(*) FROM documents"))
        return result.scalar() or 0

    def _count_chunks(self) -> int:
        result = self.db.execute(text("SELECT COUNT(*) FROM document_chunks"))
        return result.scalar() or 0

    def _check_short_content(self) -> list[AuditFinding]:
        """Flag chunks shorter than MIN_CHUNK_LENGTH."""
        findings: list[AuditFinding] = []
        rows = self.db.execute(text(
            """
            SELECT dc.id, dc.document_id, dc.chunk_text, dc.chunk_index,
                   COALESCE(d.title, 'Untitled') as title
            FROM document_chunks dc
            LEFT JOIN documents d ON dc.document_id = d.id
            WHERE LENGTH(dc.chunk_text) < :min_len
            """
        ), {"min_len": self.MIN_CHUNK_LENGTH}).fetchall()

        for row in rows:
            findings.append(AuditFinding(
                document_id=str(row[1]),
                title=str(row[4]),
                issue_type="too_short",
                severity="warning",
                description=f"分块内容过短 ({len(str(row[2]))} 字符 < {self.MIN_CHUNK_LENGTH})",
                chunk_index=row[3],
            ))
        return findings

    def _check_missing_embeddings(self) -> list[AuditFinding]:
        """Flag chunks with NULL embeddings."""
        findings: list[AuditFinding] = []
        rows = self.db.execute(text(
            """
            SELECT dc.id, dc.document_id, dc.chunk_index,
                   COALESCE(d.title, 'Untitled') as title
            FROM document_chunks dc
            LEFT JOIN documents d ON dc.document_id = d.id
            WHERE dc.chunk_embedding IS NULL
            """
        )).fetchall()

        for row in rows:
            findings.append(AuditFinding(
                document_id=str(row[1]),
                title=str(row[3]),
                issue_type="no_embedding",
                severity="critical",
                description="分块缺少向量嵌入，无法被检索",
                chunk_index=row[2],
            ))
        return findings

    def _check_duplicates(self) -> list[AuditFinding]:
        """
        Check for near-duplicate chunks using pgvector cosine distance.
        Uses sampling to avoid O(n^2) comparison on 550+ docs.
        Only checks top-N most similar pairs.
        """
        findings: list[AuditFinding] = []
        try:
            # Find pairs with cosine similarity > threshold
            # Using pgvector's <=> operator (cosine distance)
            # distance < (1 - threshold) means similarity > threshold
            max_distance = 1.0 - self.DUPLICATE_SIMILARITY_THRESHOLD
            rows = self.db.execute(text(
                """
                SELECT a.id, a.document_id, b.id, b.document_id,
                       a.chunk_embedding <=> b.chunk_embedding AS distance,
                       COALESCE(da.title, 'Untitled') as title_a,
                       COALESCE(db.title, 'Untitled') as title_b
                FROM document_chunks a
                JOIN document_chunks b ON a.id < b.id
                LEFT JOIN documents da ON a.document_id = da.id
                LEFT JOIN documents db ON b.document_id = db.id
                WHERE a.chunk_embedding IS NOT NULL
                  AND b.chunk_embedding IS NOT NULL
                  AND a.chunk_embedding <=> b.chunk_embedding < :max_dist
                LIMIT 100
                """
            ), {"max_dist": max_distance}).fetchall()

            seen_pairs: set[tuple[str, str]] = set()
            for row in rows:
                sorted_ids = sorted([str(row[0]), str(row[2])])
                pair_key: tuple[str, str] = (sorted_ids[0], sorted_ids[1])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                similarity = 1.0 - float(row[4])
                findings.append(AuditFinding(
                    document_id=str(row[1]),
                    title=f"{row[5]} ↔ {row[6]}",
                    issue_type="duplicate",
                    severity="warning",
                    description=f"高度相似分块 (相似度: {similarity:.2%})",
                ))
        except Exception as exc:
            logger.warning(
                "Duplicate check failed (pgvector may not support this query): %s",
                exc,
            )

        return findings

    def submit_to_review_queue(self, report: AuditReport) -> int:
        """Submit audit findings to kb_review_queue for Boss review."""
        from src.db.models import KBReviewQueue  # noqa: PLC0415

        count = 0
        # Submit the overall report as one review item
        report_content = report.summary()
        review_item = KBReviewQueue(
            id=uuid.uuid4(),
            content=report_content,
            source="kb_audit_pipeline",
            agent_type="system_audit",
            summary=(
                f"知识库质量审计报告: "
                f"{report.total_documents}文档, {report.flagged_documents}问题"
            ),
            status="pending",
        )
        self.db.add(review_item)
        count += 1

        # Also submit individual critical findings
        for finding in report.findings:
            if finding.severity == "critical":
                item = KBReviewQueue(
                    id=uuid.uuid4(),
                    content=(
                        f"[{finding.issue_type}] {finding.title}: "
                        f"{finding.description}"
                    ),
                    source="kb_audit_pipeline",
                    agent_type="system_audit",
                    summary=f"审计发现: {finding.issue_type} - {finding.title}",
                    status="pending",
                )
                self.db.add(item)
                count += 1

        self.db.commit()
        logger.info("Submitted %d items to KB review queue", count)
        return count


if __name__ == "__main__":
    # Also handles: python -m src.knowledge_base.audit
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        from src.db.connection import db_session
    except ImportError:
        print("ERROR: Cannot import database connection. Run from project root.")
        sys.exit(1)

    with db_session() as session:
        auditor = KBAuditor(session)
        report = auditor.audit_all()
        print(report.summary())

        # Submit to review queue
        if report.findings:
            submitted = auditor.submit_to_review_queue(report)
            print(f"\n已提交 {submitted} 条到审核队列")
        else:
            print("\n未发现质量问题，无需提交审核")
