"""
RFP Shredder - Main Orchestrator

Coordinates the complete RFP shredding workflow:
1. Extract sections (C, L, M) from RFP PDF
2. Extract requirements from each section
3. Classify requirements using Ollama
4. Save to database
5. Create opportunity and tasks
6. Generate compliance matrix
"""

import json
import logging
import sqlite3
import csv
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import uuid

from .section_parser import SectionParser
from .requirement_extractor import RequirementExtractor, Requirement
from .requirement_classifier import RequirementClassifier, RequirementClassification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RFPShredder:
    """
    Main orchestrator for RFP shredding workflow.

    Combines section parsing, requirement extraction, and classification
    into a complete end-to-end pipeline.
    """

    def __init__(
        self,
        db_path: str = "opportunities.db",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "qwen2.5:3b"
    ):
        """
        Initialize RFP Shredder.

        Args:
            db_path: Path to SQLite database
            ollama_url: URL of Ollama server
            ollama_model: Model to use for classification
        """
        self.db_path = db_path
        self.section_parser = SectionParser()
        self.req_extractor = RequirementExtractor()
        self.classifier = RequirementClassifier(
            ollama_url=ollama_url,
            model=ollama_model
        )

        # Verify database exists
        if not Path(db_path).exists():
            logger.warning(f"Database not found: {db_path}")
            logger.warning("Please run migrations/001_add_shredding_tables.py")

    def shred_rfp(
        self,
        file_path: str,
        rfp_number: str,
        opportunity_name: str,
        due_date: str,
        agency: Optional[str] = None,
        naics_code: Optional[str] = None,
        set_aside: Optional[str] = None,
        create_tasks: bool = True,
        auto_assign: bool = False,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Complete RFP shredding workflow.

        Args:
            file_path: Path to RFP PDF
            rfp_number: RFP/solicitation number
            opportunity_name: Name of opportunity
            due_date: Proposal due date (YYYY-MM-DD)
            agency: Issuing agency (optional)
            naics_code: NAICS code (optional)
            set_aside: Set-aside type (optional)
            create_tasks: Create tasks for each requirement
            auto_assign: Auto-assign tasks to team members
            output_dir: Directory for compliance matrix (default: current dir)

        Returns:
            Dictionary with results:
            {
                'status': 'success' | 'error',
                'opportunity_id': str,
                'total_requirements': int,
                'mandatory_count': int,
                'recommended_count': int,
                'optional_count': int,
                'tasks_created': int,
                'matrix_file': str,
                'sections': {...},
                'error': str (if status='error')
            }
        """
        logger.info(f"Starting RFP shredding: {rfp_number}")

        try:
            # Step 1: Extract sections
            logger.info("Step 1/6: Extracting sections (C, L, M)")
            sections = self.section_parser.extract_sections(file_path)

            # Validate critical sections
            validation = self.section_parser.validate_sections(sections)
            if not validation['is_complete']:
                logger.warning("Missing critical sections - proceeding with available sections")

            # Step 2: Extract requirements from each section
            logger.info("Step 2/6: Extracting requirements")
            all_requirements = []

            for section_letter in ['C', 'L', 'M']:
                if section_letter in sections:
                    section_data = sections[section_letter]

                    requirements = self.req_extractor.extract_requirements(
                        text=section_data['text'],
                        section=section_letter,
                        start_page=section_data.get('start_page')
                    )

                    all_requirements.extend(requirements)

            # Deduplicate
            all_requirements = self.req_extractor.deduplicate_requirements(
                all_requirements
            )

            logger.info(f"Extracted {len(all_requirements)} unique requirements")

            # Step 3: Classify requirements
            logger.info("Step 3/6: Classifying requirements with Ollama")

            # Convert to dict format for batch classification
            req_dicts = [
                {
                    'text': req.text,
                    'section': req.section,
                    'page_number': req.page_number
                }
                for req in all_requirements
            ]

            classifications = self.classifier.classify_batch(
                req_dicts,
                show_progress=True
            )

            # Merge classifications with requirements
            classified_requirements = []
            for req, classification in zip(all_requirements, classifications):
                classified_requirements.append({
                    'requirement': req,
                    'classification': classification
                })

            # Step 4: Create opportunity
            logger.info("Step 4/6: Creating opportunity")
            opportunity_id = self._create_opportunity(
                rfp_number=rfp_number,
                opportunity_name=opportunity_name,
                due_date=due_date,
                agency=agency,
                naics_code=naics_code,
                set_aside=set_aside,
                file_path=file_path,
                sections=sections,
                total_requirements=len(classified_requirements)
            )

            # Step 5: Save requirements
            logger.info("Step 5/6: Saving requirements to database")
            self._save_requirements(
                opportunity_id=opportunity_id,
                classified_requirements=classified_requirements
            )

            # Step 6: Create tasks (optional)
            tasks_created = 0
            if create_tasks:
                logger.info("Step 6/6: Creating tasks")
                tasks_created = self._create_tasks(
                    opportunity_id=opportunity_id,
                    classified_requirements=classified_requirements,
                    due_date=due_date,
                    auto_assign=auto_assign
                )

            # Generate compliance matrix
            matrix_file = self._generate_compliance_matrix(
                opportunity_id=opportunity_id,
                rfp_number=rfp_number,
                output_dir=output_dir
            )

            # Calculate statistics
            mandatory = sum(
                1 for cr in classified_requirements
                if cr['classification'].compliance_type == 'mandatory'
            )
            recommended = sum(
                1 for cr in classified_requirements
                if cr['classification'].compliance_type == 'recommended'
            )
            optional = sum(
                1 for cr in classified_requirements
                if cr['classification'].compliance_type == 'optional'
            )

            logger.info("✅ RFP shredding complete!")
            logger.info(f"  Opportunity ID: {opportunity_id}")
            logger.info(f"  Total requirements: {len(classified_requirements)}")
            logger.info(f"  Mandatory: {mandatory}")
            logger.info(f"  Recommended: {recommended}")
            logger.info(f"  Optional: {optional}")
            logger.info(f"  Tasks created: {tasks_created}")
            logger.info(f"  Matrix: {matrix_file}")

            return {
                'status': 'success',
                'opportunity_id': opportunity_id,
                'total_requirements': len(classified_requirements),
                'mandatory_count': mandatory,
                'recommended_count': recommended,
                'optional_count': optional,
                'tasks_created': tasks_created,
                'matrix_file': matrix_file,
                'sections': {
                    k: {
                        'title': v['title'],
                        'start_page': v.get('start_page'),
                        'end_page': v.get('end_page')
                    }
                    for k, v in sections.items()
                }
            }

        except Exception as e:
            logger.error(f"RFP shredding failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _create_opportunity(
        self,
        rfp_number: str,
        opportunity_name: str,
        due_date: str,
        agency: Optional[str],
        naics_code: Optional[str],
        set_aside: Optional[str],
        file_path: str,
        sections: Dict,
        total_requirements: int
    ) -> str:
        """
        Create opportunity in database.

        Returns:
            Opportunity ID
        """
        opportunity_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO opportunities (
                    id, title, description, status, due_date,
                    agency, naics_code, set_aside, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opportunity_id,
                opportunity_name,
                f"RFP {rfp_number}",
                'active',
                due_date,
                agency,
                naics_code,
                set_aside,
                json.dumps({
                    'rfp_number': rfp_number,
                    'file_path': file_path,
                    'sections': list(sections.keys()),
                    'total_requirements': total_requirements
                })
            ))

            conn.commit()
            logger.info(f"Created opportunity: {opportunity_id}")

        except Exception as e:
            logger.error(f"Failed to create opportunity: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

        return opportunity_id

    def _save_requirements(
        self,
        opportunity_id: str,
        classified_requirements: List[Dict]
    ):
        """
        Save requirements to database.

        Args:
            opportunity_id: Parent opportunity ID
            classified_requirements: List of {requirement, classification} dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for cr in classified_requirements:
                req: Requirement = cr['requirement']
                classification: RequirementClassification = cr['classification']

                cursor.execute("""
                    INSERT INTO requirements (
                        id, opportunity_id, section, page_number,
                        paragraph_id, source_text, compliance_type,
                        requirement_category, priority, risk_level,
                        compliance_status, keywords, extracted_entities,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    req.id,
                    opportunity_id,
                    req.section,
                    req.page_number,
                    req.paragraph_id,
                    req.text,
                    classification.compliance_type,
                    classification.category,
                    classification.priority,
                    classification.risk_level,
                    'not_started',
                    json.dumps(classification.keywords),
                    json.dumps(classification.extracted_entities),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

            conn.commit()
            logger.info(f"Saved {len(classified_requirements)} requirements")

        except Exception as e:
            logger.error(f"Failed to save requirements: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_tasks(
        self,
        opportunity_id: str,
        classified_requirements: List[Dict],
        due_date: str,
        auto_assign: bool = False
    ) -> int:
        """
        Create tasks for requirements.

        Args:
            opportunity_id: Parent opportunity ID
            classified_requirements: List of requirements
            due_date: Proposal due date
            auto_assign: Auto-assign to team members

        Returns:
            Number of tasks created
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        tasks_created = 0

        try:
            # Parse due date
            proposal_due = datetime.fromisoformat(due_date)

            for cr in classified_requirements:
                req: Requirement = cr['requirement']
                classification: RequirementClassification = cr['classification']

                # Calculate task due date (7 days before proposal due)
                task_due = proposal_due - timedelta(days=7)

                # Determine assignee
                assignee = None
                assignee_type = None

                if auto_assign:
                    # Simple auto-assignment logic
                    if classification.category == 'technical':
                        assignee = 'agent-technical'
                        assignee_type = 'agent'
                    elif classification.category == 'management':
                        assignee = 'agent-management'
                        assignee_type = 'agent'
                    elif classification.category == 'cost':
                        assignee = 'agent-cost'
                        assignee_type = 'agent'

                # Create task
                task_id = str(uuid.uuid4())

                cursor.execute("""
                    INSERT INTO tasks (
                        id, opportunity_id, title, description,
                        status, priority, due_date, assignee,
                        metadata, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    opportunity_id,
                    f"{req.id}: {req.text[:80]}...",
                    req.text,
                    'pending',
                    classification.priority,
                    task_due.isoformat(),
                    assignee,
                    json.dumps({
                        'requirement_id': req.id,
                        'section': req.section,
                        'compliance_type': classification.compliance_type,
                        'category': classification.category,
                        'assignee_type': assignee_type
                    }),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                # Update requirement with task_id
                cursor.execute("""
                    UPDATE requirements
                    SET task_id = ?, assignee_id = ?, assignee_type = ?
                    WHERE id = ?
                """, (task_id, assignee, assignee_type, req.id))

                tasks_created += 1

            conn.commit()
            logger.info(f"Created {tasks_created} tasks")

        except Exception as e:
            logger.error(f"Failed to create tasks: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

        return tasks_created

    def _generate_compliance_matrix(
        self,
        opportunity_id: str,
        rfp_number: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Generate compliance matrix CSV.

        Args:
            opportunity_id: Opportunity ID
            rfp_number: RFP number for filename
            output_dir: Output directory (default: current dir)

        Returns:
            Path to generated CSV file
        """
        # Query requirements
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, section, page_number, paragraph_id, source_text,
                compliance_type, requirement_category, priority, risk_level,
                compliance_status, proposal_section, proposal_page,
                assignee_id, assignee_type, assignee_name,
                keywords, notes, created_at, due_date
            FROM requirements
            WHERE opportunity_id = ?
            ORDER BY section, id
        """, (opportunity_id,))

        requirements = cursor.fetchall()
        conn.close()

        # Generate filename
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.cwd()

        output_path.mkdir(parents=True, exist_ok=True)

        csv_file = output_path / f"{rfp_number}_compliance_matrix.csv"

        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Req ID', 'Section', 'Page', 'Paragraph',
                'Requirement Text', 'Compliance Type', 'Category',
                'Priority', 'Risk', 'Compliance Status',
                'Proposal Section', 'Proposal Page',
                'Assigned To', 'Assignee Type', 'Assignee Name',
                'Keywords', 'Notes', 'Due Date'
            ])

            # Data rows
            for req in requirements:
                writer.writerow([
                    req[0],  # id
                    req[1],  # section
                    req[2],  # page_number
                    req[3],  # paragraph_id
                    req[4],  # source_text
                    req[5],  # compliance_type
                    req[6],  # requirement_category
                    req[7],  # priority
                    req[8],  # risk_level
                    req[9],  # compliance_status
                    req[10],  # proposal_section
                    req[11],  # proposal_page
                    req[12],  # assignee_id
                    req[13],  # assignee_type
                    req[14],  # assignee_name
                    req[15],  # keywords
                    req[16],  # notes
                    req[18]   # due_date
                ])

        logger.info(f"Generated compliance matrix: {csv_file}")
        return str(csv_file)

    def get_opportunity_status(self, opportunity_id: str) -> Dict:
        """
        Get status of shredded opportunity.

        Args:
            opportunity_id: Opportunity ID

        Returns:
            Status dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get opportunity
        cursor.execute("""
            SELECT title, status, due_date, metadata
            FROM opportunities
            WHERE id = ?
        """, (opportunity_id,))

        opp = cursor.fetchone()

        if not opp:
            conn.close()
            return {'error': 'Opportunity not found'}

        # Get requirements stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN compliance_type = 'mandatory' THEN 1 ELSE 0 END) as mandatory,
                SUM(CASE WHEN compliance_status = 'fully_compliant' THEN 1 ELSE 0 END) as compliant,
                SUM(CASE WHEN compliance_status = 'partially_compliant' THEN 1 ELSE 0 END) as partial,
                SUM(CASE WHEN compliance_status = 'non_compliant' THEN 1 ELSE 0 END) as non_compliant,
                SUM(CASE WHEN compliance_status = 'not_started' THEN 1 ELSE 0 END) as not_started
            FROM requirements
            WHERE opportunity_id = ?
        """, (opportunity_id,))

        req_stats = cursor.fetchone()

        # Get task stats
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM tasks
            WHERE opportunity_id = ?
        """, (opportunity_id,))

        task_stats = cursor.fetchone()

        conn.close()

        return {
            'opportunity': {
                'id': opportunity_id,
                'title': opp[0],
                'status': opp[1],
                'due_date': opp[2],
                'metadata': json.loads(opp[3]) if opp[3] else {}
            },
            'requirements': {
                'total': req_stats[0],
                'mandatory': req_stats[1],
                'compliant': req_stats[2],
                'partial': req_stats[3],
                'non_compliant': req_stats[4],
                'not_started': req_stats[5],
                'completion_rate': round(req_stats[2] / req_stats[0] * 100, 1) if req_stats[0] > 0 else 0
            },
            'tasks': {
                'total': task_stats[0] if task_stats[0] else 0,
                'completed': task_stats[1] if task_stats[1] else 0,
                'in_progress': task_stats[2] if task_stats[2] else 0,
                'pending': task_stats[3] if task_stats[3] else 0
            }
        }
