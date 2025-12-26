"""
Career-Monster API routes.

Handles manual entry of hiring positions and candidates, and generates assessments.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def handle_career_positions_list_api(handler):
    """
    Handle GET /api/career/positions - List all positions.

    Query params:
        institution: Filter by institution name (optional)
        field: Filter by field specialty (optional)
        limit: Maximum results (default 50)
    """
    try:
        from career_monster import CareerDatabase

        # Parse query parameters
        query_params = handler.get_query_params()
        institution = query_params.get('institution')
        field = query_params.get('field')
        limit = int(query_params.get('limit', 50))

        db = CareerDatabase()
        positions = db.list_positions(institution=institution, field=field, limit=limit)

        handler.send_json_response({
            'status': 'success',
            'positions': [pos.model_dump() for pos in positions],
            'count': len(positions)
        })

    except Exception as e:
        logger.error(f"Error listing positions: {e}")
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


def handle_career_positions_create_api(handler):
    """
    Handle POST /api/career/positions - Create new position.

    Request body:
    {
        "institution": "Harvard University",
        "department": "Government",
        "position_title": "Assistant Professor",
        "field_specialty": "Political Science",
        "hire_date": "2024-07-01",
        "job_posting_url": "https://...",
        "department_research_areas": ["Democracy", "Political Economy", ...]
    }
    """
    try:
        from career_monster import CareerDatabase, HiringPosition

        data = handler.get_request_body()

        # Validate required fields
        required = ['institution', 'department', 'position_title', 'field_specialty', 'hire_date']
        missing = [f for f in required if f not in data]
        if missing:
            handler.send_json_response({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing)}'
            }, 400)
            return

        # Create position object
        position = HiringPosition(
            institution=data['institution'],
            department=data['department'],
            position_title=data['position_title'],
            field_specialty=data['field_specialty'],
            hire_date=data['hire_date'],
            job_posting_url=data.get('job_posting_url'),
            department_research_areas=data.get('department_research_areas', [])
        )

        db = CareerDatabase()
        position_id = db.create_position(position)

        handler.send_json_response({
            'status': 'success',
            'position_id': position_id,
            'message': f'Position created: {data["institution"]} - {data["position_title"]}'
        })

    except Exception as e:
        logger.error(f"Error creating position: {e}")
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


def handle_career_candidates_create_api(handler):
    """
    Handle POST /api/career/candidates - Create new candidate.

    Request body:
    {
        "position_id": "pos_001",
        "name": "Jane Doe",
        "phd_institution": "Stanford University",
        "phd_year": 2023,
        "phd_advisor": "John Smith",
        "dissertation_title": "Democratic Accountability in Hybrid Regimes",
        "dissertation_keywords": ["democracy", "accountability", ...],
        "dissertation_abstract": "This dissertation...",
        "publications_count": 5,
        "citations_count": 100,
        "co_authors": ["Alice", "Bob", ...]
    }
    """
    try:
        from career_monster import CareerDatabase, Candidate

        data = handler.get_request_body()

        # Validate required fields
        required = ['position_id', 'name', 'phd_institution', 'phd_year', 'dissertation_title']
        missing = [f for f in required if f not in data]
        if missing:
            handler.send_json_response({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing)}'
            }, 400)
            return

        # Create candidate object
        candidate = Candidate(
            name=data['name'],
            phd_institution=data['phd_institution'],
            phd_year=data['phd_year'],
            phd_advisor=data.get('phd_advisor'),
            dissertation_title=data['dissertation_title'],
            dissertation_keywords=data.get('dissertation_keywords', []),
            dissertation_abstract=data.get('dissertation_abstract', ''),
            publications_count=data.get('publications_count', 0),
            citations_count=data.get('citations_count', 0),
            co_authors=data.get('co_authors', [])
        )

        db = CareerDatabase()
        candidate_id = db.create_candidate(candidate, data['position_id'])

        handler.send_json_response({
            'status': 'success',
            'candidate_id': candidate_id,
            'message': f'Candidate created: {data["name"]}'
        })

    except Exception as e:
        logger.error(f"Error creating candidate: {e}")
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


def handle_career_analyze_api(handler):
    """
    Handle POST /api/career/analyze - Generate assessment for candidate.

    Request body:
    {
        "candidate_id": "cand_001",
        "position_id": "pos_001",
        "verbosity": "standard"  // brief, standard, detailed, comprehensive
    }
    """
    try:
        from career_monster import (
            CareerDatabase, AlignmentScorer, NarrativeGenerator
        )

        data = handler.get_request_body()

        # Validate required fields
        if 'candidate_id' not in data or 'position_id' not in data:
            handler.send_json_response({
                'status': 'error',
                'message': 'Missing required fields: candidate_id, position_id'
            }, 400)
            return

        candidate_id = data['candidate_id']
        position_id = data['position_id']
        verbosity = data.get('verbosity', 'standard')

        # Load data from database
        db = CareerDatabase()
        candidate = db.get_candidate(candidate_id)
        position = db.get_position(position_id)

        if not candidate:
            handler.send_json_response({
                'status': 'error',
                'message': f'Candidate not found: {candidate_id}'
            }, 404)
            return

        if not position:
            handler.send_json_response({
                'status': 'error',
                'message': f'Position not found: {position_id}'
            }, 404)
            return

        # Run analysis
        scorer = AlignmentScorer()
        alignment = scorer.calculate_alignment(candidate, position)
        network = scorer.analyze_network(candidate)
        confidence = scorer.calculate_confidence(candidate, position)

        # Generate narratives
        generator = NarrativeGenerator()
        assessment = generator.generate_assessment(
            candidate=candidate,
            position=position,
            alignment=alignment,
            network=network,
            verbosity=verbosity
        )

        # Set confidence score
        assessment.confidence_score = confidence

        # Save assessment
        assessment_id = db.create_assessment(assessment, candidate_id, position_id)

        # Return result
        handler.send_json_response({
            'status': 'success',
            'assessment_id': assessment_id,
            'alignment_score': alignment.model_dump(),
            'network_analysis': network.model_dump(),
            'confidence_score': confidence.model_dump(),
            'narratives': {
                'optimistic': assessment.optimistic_narrative,
                'pessimistic': assessment.pessimistic_narrative,
                'pragmatic': assessment.pragmatic_narrative,
                'speculative': assessment.speculative_narrative
            },
            'success_factors': assessment.key_success_factors,
            'red_flags': assessment.potential_red_flags
        })

    except Exception as e:
        logger.error(f"Error generating assessment: {e}")
        import traceback
        traceback.print_exc()
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


def handle_career_assessment_get_api(handler, assessment_id):
    """
    Handle GET /api/career/assessments/{id} - Get assessment by ID.
    """
    try:
        from career_monster import CareerDatabase

        db = CareerDatabase()
        assessment = db.get_assessment(assessment_id)

        if not assessment:
            handler.send_json_response({
                'status': 'error',
                'message': f'Assessment not found: {assessment_id}'
            }, 404)
            return

        handler.send_json_response({
            'status': 'success',
            'assessment': assessment.model_dump()
        })

    except Exception as e:
        logger.error(f"Error retrieving assessment: {e}")
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)


def handle_career_stats_api(handler):
    """
    Handle GET /api/career/stats - Get summary statistics.
    """
    try:
        from career_monster import CareerDatabase

        db = CareerDatabase()
        stats = db.get_summary_stats()

        handler.send_json_response({
            'status': 'success',
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        handler.send_json_response({
            'status': 'error',
            'message': str(e)
        }, 500)
