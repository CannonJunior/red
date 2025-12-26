"""
Database operations for career-monster skill.

Handles all database interactions for positions, candidates, and assessments.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .data_models import (
    HiringPosition,
    Candidate,
    HiringAssessment,
    AlignmentScore,
    NetworkAnalysis,
    ConfidenceScore,
    Publication,
    Award
)

logger = logging.getLogger(__name__)


class CareerDatabase:
    """Database manager for career-monster."""

    def __init__(self, db_path: str = "opportunities.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure career-monster tables exist."""
        migration_file = Path(__file__).parent.parent / "migrations" / "001_career_monster.sql"

        if not migration_file.exists():
            logger.warning(f"Migration file not found: {migration_file}")
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Read migration
            with open(migration_file, 'r') as f:
                migration_sql = f.read()

            # Remove comment-only lines
            lines = [
                line for line in migration_sql.split('\n')
                if line.strip() and not line.strip().startswith('--')
            ]
            cleaned_sql = '\n'.join(lines)

            # Execute entire script using executescript (handles CREATE TABLE IF NOT EXISTS properly)
            try:
                cursor.executescript(cleaned_sql)
                conn.commit()
                logger.info("Career-monster schema initialized")
            except sqlite3.OperationalError as e:
                # Table already exists - this is OK
                if "already exists" not in str(e):
                    logger.error(f"Migration error: {e}")
                    raise

    # ========== Position Operations ==========

    def create_position(self, position: HiringPosition) -> str:
        """
        Create a new hiring position.

        Args:
            position: HiringPosition object

        Returns:
            Position ID
        """
        position_id = position.id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO career_positions (
                    id, opportunity_id, institution, department, position_title,
                    field_specialty, hire_date, job_posting_url,
                    department_research_areas, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                position_id,
                None,  # opportunity_id - can be linked later
                position.institution,
                position.department,
                position.position_title,
                position.field_specialty,
                position.hire_date,
                position.job_posting_url,
                json.dumps(position.department_research_areas),
                now,
                now
            ))
            conn.commit()

        logger.info(f"Created position: {position_id}")
        return position_id

    def get_position(self, position_id: str) -> Optional[HiringPosition]:
        """
        Retrieve a position by ID.

        Args:
            position_id: Position ID

        Returns:
            HiringPosition or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, institution, department, position_title, field_specialty,
                       hire_date, job_posting_url, department_research_areas
                FROM career_positions WHERE id = ?
            """, (position_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return HiringPosition(
                id=row[0],
                institution=row[1],
                department=row[2],
                position_title=row[3],
                field_specialty=row[4],
                hire_date=row[5],
                job_posting_url=row[6],
                department_research_areas=json.loads(row[7]) if row[7] else []
            )

    def list_positions(
        self,
        institution: Optional[str] = None,
        field: Optional[str] = None,
        limit: int = 50
    ) -> List[HiringPosition]:
        """
        List hiring positions with optional filters.

        Args:
            institution: Filter by institution name
            field: Filter by field specialty
            limit: Maximum number of results

        Returns:
            List of HiringPosition objects
        """
        query = """
            SELECT id, institution, department, position_title, field_specialty,
                   hire_date, job_posting_url, department_research_areas
            FROM career_positions WHERE 1=1
        """
        params = []

        if institution:
            query += " AND institution LIKE ?"
            params.append(f"%{institution}%")

        if field:
            query += " AND field_specialty LIKE ?"
            params.append(f"%{field}%")

        query += " ORDER BY hire_date DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            positions = []
            for row in cursor.fetchall():
                positions.append(HiringPosition(
                    id=row[0],
                    institution=row[1],
                    department=row[2],
                    position_title=row[3],
                    field_specialty=row[4],
                    hire_date=row[5],
                    job_posting_url=row[6],
                    department_research_areas=json.loads(row[7]) if row[7] else []
                ))

            return positions

    # ========== Candidate Operations ==========

    def create_candidate(self, candidate: Candidate, position_id: str) -> str:
        """
        Create a new candidate record.

        Args:
            candidate: Candidate object
            position_id: Associated position ID

        Returns:
            Candidate ID
        """
        candidate_id = candidate.id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO career_candidates (
                    id, position_id, name, current_position, phd_institution,
                    phd_year, phd_advisor, dissertation_title, dissertation_url,
                    dissertation_keywords, dissertation_abstract, publications_data,
                    publications_count, co_authors, awards_data, citations_count,
                    h_index, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate_id,
                position_id,
                candidate.name,
                candidate.current_position,
                candidate.phd_institution,
                candidate.phd_year,
                candidate.phd_advisor,
                candidate.dissertation_title,
                candidate.dissertation_url,
                json.dumps(candidate.dissertation_keywords),
                candidate.dissertation_abstract,
                json.dumps([pub.model_dump() for pub in candidate.publications]),
                candidate.publications_count,
                json.dumps(candidate.co_authors),
                json.dumps([award.model_dump() for award in candidate.awards]),
                candidate.citations_count,
                candidate.h_index,
                now,
                now
            ))
            conn.commit()

        logger.info(f"Created candidate: {candidate_id}")
        return candidate_id

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """
        Retrieve a candidate by ID.

        Args:
            candidate_id: Candidate ID

        Returns:
            Candidate or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, position_id, name, current_position, phd_institution,
                       phd_year, phd_advisor, dissertation_title, dissertation_url,
                       dissertation_keywords, dissertation_abstract, publications_data,
                       publications_count, co_authors, awards_data, citations_count,
                       h_index
                FROM career_candidates WHERE id = ?
            """, (candidate_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Reconstruct Candidate object
            publications_data = json.loads(row[11]) if row[11] else []
            publications = [Publication(**pub) for pub in publications_data]

            awards_data = json.loads(row[14]) if row[14] else []
            awards = [Award(**award) for award in awards_data]

            return Candidate(
                id=row[0],
                position_id=row[1],
                name=row[2],
                current_position=row[3],
                phd_institution=row[4],
                phd_year=row[5],
                phd_advisor=row[6],
                dissertation_title=row[7],
                dissertation_url=row[8],
                dissertation_keywords=json.loads(row[9]) if row[9] else [],
                dissertation_abstract=row[10],
                publications=publications,
                publications_count=row[12],
                co_authors=json.loads(row[13]) if row[13] else [],
                awards=awards,
                citations_count=row[15],
                h_index=row[16]
            )

    # ========== Assessment Operations ==========

    def create_assessment(
        self,
        assessment: HiringAssessment,
        candidate_id: str,
        position_id: str
    ) -> str:
        """
        Create a new hiring assessment.

        Args:
            assessment: HiringAssessment object
            candidate_id: Candidate ID
            position_id: Position ID

        Returns:
            Assessment ID
        """
        assessment_id = assessment.id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO career_assessments (
                    id, candidate_id, position_id,
                    topic_alignment, network_overlap, methodology_match,
                    publication_strength, overall_score,
                    total_collaborators, star_collaborators, institutional_diversity,
                    network_quality_score,
                    confidence_overall, confidence_data_quality, confidence_analysis_robustness,
                    optimistic_narrative, pessimistic_narrative, pragmatic_narrative,
                    speculative_narrative, success_factors, red_flags,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_id,
                candidate_id,
                position_id,
                assessment.alignment_score.topic_alignment,
                assessment.alignment_score.network_overlap,
                assessment.alignment_score.methodology_match,
                assessment.alignment_score.publication_strength,
                assessment.alignment_score.overall_score,
                assessment.network_analysis.total_collaborators,
                json.dumps(assessment.network_analysis.star_collaborators),
                assessment.network_analysis.institutional_diversity,
                assessment.network_analysis.network_quality_score,
                assessment.confidence_score.overall,
                assessment.confidence_score.data_quality,
                assessment.confidence_score.analysis_robustness,
                assessment.optimistic_narrative,
                assessment.pessimistic_narrative,
                assessment.pragmatic_narrative,
                assessment.speculative_narrative,
                json.dumps(assessment.key_success_factors),
                json.dumps(assessment.potential_red_flags),
                now,
                now
            ))
            conn.commit()

        logger.info(f"Created assessment: {assessment_id}")
        return assessment_id

    def get_assessment(self, assessment_id: str) -> Optional[HiringAssessment]:
        """
        Retrieve an assessment by ID.

        Args:
            assessment_id: Assessment ID

        Returns:
            HiringAssessment or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, candidate_id, position_id,
                       topic_alignment, network_overlap, methodology_match,
                       publication_strength, overall_score,
                       total_collaborators, star_collaborators, institutional_diversity,
                       network_quality_score,
                       confidence_overall, confidence_data_quality, confidence_analysis_robustness,
                       optimistic_narrative, pessimistic_narrative, pragmatic_narrative,
                       speculative_narrative, success_factors, red_flags
                FROM career_assessments WHERE id = ?
            """, (assessment_id,))

            row = cursor.fetchone()
            if not row:
                return None

            # Reconstruct nested objects
            alignment_score = AlignmentScore(
                topic_alignment=row[3],
                network_overlap=row[4],
                methodology_match=row[5],
                publication_strength=row[6],
                overall_score=row[7]
            )

            network_analysis = NetworkAnalysis(
                total_collaborators=row[8],
                star_collaborators=json.loads(row[9]) if row[9] else [],
                institutional_diversity=row[10],
                network_quality_score=row[11]
            )

            confidence_score = ConfidenceScore(
                overall=row[12],
                data_quality=row[13],
                analysis_robustness=row[14]
            )

            return HiringAssessment(
                id=row[0],
                candidate_id=row[1],
                position_id=row[2],
                alignment_score=alignment_score,
                network_analysis=network_analysis,
                confidence_score=confidence_score,
                optimistic_narrative=row[15],
                pessimistic_narrative=row[16],
                pragmatic_narrative=row[17],
                speculative_narrative=row[18],
                key_success_factors=json.loads(row[19]) if row[19] else [],
                potential_red_flags=json.loads(row[20]) if row[20] else []
            )

    def get_assessments_for_position(self, position_id: str) -> List[HiringAssessment]:
        """
        Get all assessments for a position.

        Args:
            position_id: Position ID

        Returns:
            List of HiringAssessment objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM career_assessments WHERE position_id = ?
            """, (position_id,))

            assessment_ids = [row[0] for row in cursor.fetchall()]
            return [self.get_assessment(aid) for aid in assessment_ids if aid]

    # ========== Analytics Operations ==========

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for career analysis.

        Returns:
            Dictionary with summary stats
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Count positions
            cursor.execute("SELECT COUNT(*) FROM career_positions")
            total_positions = cursor.fetchone()[0]

            # Count candidates
            cursor.execute("SELECT COUNT(*) FROM career_candidates")
            total_candidates = cursor.fetchone()[0]

            # Count assessments
            cursor.execute("SELECT COUNT(*) FROM career_assessments")
            total_assessments = cursor.fetchone()[0]

            # Average scores
            cursor.execute("""
                SELECT AVG(overall_score), AVG(topic_alignment),
                       AVG(publication_strength), AVG(network_quality_score)
                FROM career_assessments
            """)
            avg_row = cursor.fetchone()

            # Top institutions
            cursor.execute("""
                SELECT phd_institution, COUNT(*) as count
                FROM career_candidates
                GROUP BY phd_institution
                ORDER BY count DESC
                LIMIT 10
            """)
            top_institutions = [
                {"institution": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            return {
                "total_positions": total_positions,
                "total_candidates": total_candidates,
                "total_assessments": total_assessments,
                "avg_overall_score": round(avg_row[0], 2) if avg_row[0] else 0,
                "avg_topic_alignment": round(avg_row[1], 2) if avg_row[1] else 0,
                "avg_publication_strength": round(avg_row[2], 2) if avg_row[2] else 0,
                "avg_network_quality": round(avg_row[3], 2) if avg_row[3] else 0,
                "top_phd_institutions": top_institutions
            }
