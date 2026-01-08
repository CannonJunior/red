"""
Shredding Tools for Agent Function Calling

Provides RFP shredding capabilities that agents can invoke via tool calls.
"""

import logging
import re
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from shredding import RFPShredder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def shred_rfp(
    file_path: str,
    rfp_number: str,
    opportunity_name: str,
    due_date: str,
    agency: Optional[str] = None,
    naics_code: Optional[str] = None,
    set_aside: Optional[str] = None,
    create_tasks: bool = True,
    auto_assign: bool = False
) -> Dict:
    """
    Shred an RFP document into structured requirements.

    Analyzes government RFP documents to extract sections (C, L, M),
    identify requirements, classify them using local LLM, and generate
    compliance matrices for proposal tracking.

    Args:
        file_path: Path to RFP PDF or text file (relative or absolute)
        rfp_number: RFP/solicitation number (e.g., "FA8612-21-S-C001")
        opportunity_name: Name of the opportunity
        due_date: Proposal due date in YYYY-MM-DD format
        agency: Issuing agency (optional, e.g., "Air Force")
        naics_code: NAICS code (optional, e.g., "541512")
        set_aside: Set-aside type (optional, e.g., "Small Business")
        create_tasks: Whether to create tasks for each requirement
        auto_assign: Whether to auto-assign tasks to agents

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
            'matrix_file': str,  # Path to generated compliance matrix CSV
            'sections': {...},
            'error': str (if status='error')
        }

    Example:
        [TOOL_CALL:shred_rfp]
        {
            "file_path": "data/JADC2/FA8612-21-S-C001.txt",
            "rfp_number": "FA8612-21-S-C001",
            "opportunity_name": "JADC2 Cloud Services",
            "due_date": "2025-02-15",
            "agency": "Air Force",
            "create_tasks": true
        }
        [/TOOL_CALL]
    """
    logger.info(f"Agent tool call: shred_rfp({rfp_number if rfp_number else 'UNKNOWN'})")

    try:
        # Validate required parameters
        if not file_path or not file_path.strip():
            return {
                'status': 'error',
                'error': 'file_path is required and cannot be empty'
            }

        if not rfp_number or not rfp_number.strip():
            return {
                'status': 'error',
                'error': 'rfp_number is required and cannot be empty'
            }

        if not opportunity_name or not opportunity_name.strip():
            return {
                'status': 'error',
                'error': 'opportunity_name is required and cannot be empty'
            }

        if not due_date or not due_date.strip():
            return {
                'status': 'error',
                'error': 'due_date is required and cannot be empty (format: YYYY-MM-DD)'
            }

        # Validate due_date format
        try:
            datetime.fromisoformat(due_date)
        except ValueError:
            return {
                'status': 'error',
                'error': f'Invalid due_date format: "{due_date}". Must be YYYY-MM-DD (e.g., "2025-02-15")'
            }

        # Resolve file path (handle relative paths from project root)
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            # Assume relative to project root
            project_root = Path(__file__).parent.parent
            file_path_obj = project_root / file_path

        if not file_path_obj.exists():
            return {
                'status': 'error',
                'error': f'File not found: {file_path}'
            }

        # Check if path is a directory (common mistake)
        if file_path_obj.is_dir():
            return {
                'status': 'error',
                'error': f'Path is a directory, not a file: {file_path}. Use shred_directory() to process multiple files, or specify a single file like "data/JADC2/FA8612-21-S-C001.txt"'
            }

        # Initialize shredder
        shredder = RFPShredder(
            db_path="opportunities.db",
            ollama_url="http://localhost:11434",
            ollama_model="qwen2.5:3b"
        )

        # Shred the RFP
        result = shredder.shred_rfp(
            file_path=str(file_path_obj),
            rfp_number=rfp_number,
            opportunity_name=opportunity_name,
            due_date=due_date,
            agency=agency,
            naics_code=naics_code,
            set_aside=set_aside,
            create_tasks=create_tasks,
            auto_assign=auto_assign,
            output_dir=None  # Use default outputs/shredding/compliance-matrices/
        )

        logger.info(f"✅ Shredding complete: {result.get('total_requirements', 0)} requirements extracted")
        return result

    except Exception as e:
        logger.error(f"Shredding tool error: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def get_opportunity_status(opportunity_id: str) -> Dict:
    """
    Get the status of a shredded RFP opportunity.

    Retrieves statistics and progress for a previously shredded RFP,
    including requirement counts, compliance status, and task completion.

    Args:
        opportunity_id: UUID of the opportunity

    Returns:
        Dictionary with opportunity status:
        {
            'opportunity': {
                'id': str,
                'title': str,
                'status': str,
                'due_date': str,
                'metadata': {...}
            },
            'requirements': {
                'total': int,
                'mandatory': int,
                'compliant': int,
                'partial': int,
                'non_compliant': int,
                'not_started': int,
                'completion_rate': float
            },
            'tasks': {
                'total': int,
                'completed': int,
                'in_progress': int,
                'pending': int
            }
        }

    Example:
        [TOOL_CALL:get_opportunity_status]
        {"opportunity_id": "550e8400-e29b-41d4-a716-446655440000"}
        [/TOOL_CALL]
    """
    logger.info(f"Agent tool call: get_opportunity_status({opportunity_id})")

    try:
        shredder = RFPShredder(db_path="opportunities.db")
        return shredder.get_opportunity_status(opportunity_id)

    except Exception as e:
        logger.error(f"Status tool error: {e}")
        return {'error': str(e)}


def shred_directory(
    directory_path: str,
    default_due_date: str = "2025-12-31",
    agency: Optional[str] = None,
    create_tasks: bool = True
) -> Dict:
    """
    Shred all RFP documents in a directory.

    Processes all PDF and TXT files in the specified directory, extracting
    requirements and generating compliance matrices for each.

    Args:
        directory_path: Path to directory containing RFP files
        default_due_date: Default due date if not specified (YYYY-MM-DD)
        agency: Issuing agency (optional, e.g., "Air Force")
        create_tasks: Whether to create tasks for each requirement

    Returns:
        Dictionary with aggregated results:
        {
            'status': 'success' | 'partial' | 'error',
            'files_processed': int,
            'files_failed': int,
            'total_requirements': int,
            'opportunities': [
                {
                    'file': str,
                    'opportunity_id': str,
                    'rfp_number': str,
                    'requirements': int,
                    'matrix_file': str
                },
                ...
            ],
            'errors': [str, ...],
            'summary': str
        }

    Example:
        [TOOL_CALL:shred_directory]
        {
            "directory_path": "data/JADC2",
            "default_due_date": "2025-06-30",
            "agency": "Air Force"
        }
        [/TOOL_CALL]
    """
    logger.info(f"Agent tool call: shred_directory({directory_path})")

    try:
        # Validate due_date format
        try:
            datetime.fromisoformat(default_due_date)
        except ValueError:
            return {
                'status': 'error',
                'error': f'Invalid default_due_date format: "{default_due_date}". Must be YYYY-MM-DD'
            }

        # Resolve directory path
        dir_path = Path(directory_path)
        if not dir_path.is_absolute():
            project_root = Path(__file__).parent.parent
            dir_path = project_root / directory_path

        if not dir_path.exists():
            return {
                'status': 'error',
                'error': f'Directory not found: {directory_path}'
            }

        if not dir_path.is_dir():
            return {
                'status': 'error',
                'error': f'Path is not a directory: {directory_path}. Use shred_rfp() for single files.'
            }

        # Find all RFP files (PDF and TXT)
        rfp_files = []
        for pattern in ['*.pdf', '*.txt', '*.PDF', '*.TXT']:
            rfp_files.extend(dir_path.glob(pattern))

        if not rfp_files:
            return {
                'status': 'error',
                'error': f'No PDF or TXT files found in directory: {directory_path}'
            }

        logger.info(f"Found {len(rfp_files)} RFP files to process")

        # Process each file
        results = []
        errors = []
        total_requirements = 0
        files_processed = 0
        files_failed = 0

        for file_path in sorted(rfp_files):
            logger.info(f"Processing: {file_path.name}")

            # Extract RFP number from filename
            # Common patterns: FA8612-21-S-C001, CSO-001, etc.
            filename = file_path.stem
            rfp_number = _extract_rfp_number(filename)

            # Generate opportunity name from filename
            opportunity_name = _generate_opportunity_name(filename)

            try:
                result = shred_rfp(
                    file_path=str(file_path),
                    rfp_number=rfp_number,
                    opportunity_name=opportunity_name,
                    due_date=default_due_date,
                    agency=agency or "Unknown",
                    create_tasks=create_tasks,
                    auto_assign=False
                )

                if result['status'] == 'success':
                    files_processed += 1
                    total_requirements += result.get('total_requirements', 0)
                    results.append({
                        'file': file_path.name,
                        'opportunity_id': result['opportunity_id'],
                        'rfp_number': rfp_number,
                        'requirements': result['total_requirements'],
                        'mandatory': result['mandatory_count'],
                        'optional': result['optional_count'],
                        'matrix_file': result['matrix_file']
                    })
                    logger.info(f"✅ {file_path.name}: {result['total_requirements']} requirements")
                else:
                    files_failed += 1
                    error_msg = f"{file_path.name}: {result.get('error', 'Unknown error')}"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")

            except Exception as e:
                files_failed += 1
                error_msg = f"{file_path.name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        # Generate summary
        status = 'success' if files_failed == 0 else ('partial' if files_processed > 0 else 'error')
        summary = f"Processed {files_processed}/{len(rfp_files)} files successfully. "
        summary += f"Extracted {total_requirements} total requirements."
        if files_failed > 0:
            summary += f" {files_failed} files failed."

        return {
            'status': status,
            'files_processed': files_processed,
            'files_failed': files_failed,
            'total_files': len(rfp_files),
            'total_requirements': total_requirements,
            'opportunities': results,
            'errors': errors,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"Directory shredding error: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def _extract_rfp_number(filename: str) -> str:
    """
    Extract RFP number from filename.

    Tries common patterns like FA8612-21-S-C001, CSO-001, etc.
    Falls back to using the filename if no pattern matches.
    """
    # Pattern 1: FAR-style (FA8612-21-S-C001)
    match = re.search(r'[A-Z]{2}\d{4}-\d{2}-[A-Z]-[A-Z]\d{3}', filename)
    if match:
        return match.group(0)

    # Pattern 2: CSO-style (CSO-001, CSO_Call_001)
    match = re.search(r'CSO[_\s-]*(?:Call[_\s-]*)?(\d{3})', filename, re.IGNORECASE)
    if match:
        return f"CSO-{match.group(1)}"

    # Pattern 3: Generic number pattern (001, 002, etc.)
    match = re.search(r'(\d{3,4})', filename)
    if match:
        return f"RFP-{match.group(1)}"

    # Fallback: use filename (sanitized)
    sanitized = re.sub(r'[^\w\-]', '-', filename)
    return sanitized[:50]  # Limit length


def _generate_opportunity_name(filename: str) -> str:
    """
    Generate human-readable opportunity name from filename.

    Converts filenames like "JADC2_CSO_Call_003_SPOC" to "JADC2 CSO Call 003 SPOC"
    """
    # Remove file extension
    name = Path(filename).stem

    # Replace underscores and multiple spaces with single space
    name = re.sub(r'[_+]+', ' ', name)
    name = re.sub(r'\s+', ' ', name)

    # Remove dates in format YYYYMMDD
    name = re.sub(r'\b\d{8}\b', '', name)

    # Clean up
    name = name.strip()

    # Limit length
    if len(name) > 100:
        name = name[:97] + "..."

    return name if name else "Unknown Opportunity"
