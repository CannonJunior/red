"""
Career Analysis List API Routes

Provides endpoints for managing career-monster analysis results in list view.
"""

import sqlite3
import json
from typing import List, Dict, Any

# Database path
DB_PATH = "opportunities.db"


def get_career_list() -> Dict[str, Any]:
    """Get all career analysis list items."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                assessment_id,
                position_id,
                candidate_id,
                candidate_name,
                institution,
                department,
                position_title,
                hire_date,
                phd_institution,
                phd_year,
                overall_score,
                topic_alignment,
                publication_strength,
                network_overlap,
                methodology_match,
                publications_count,
                citations_count,
                confidence_score,
                tags,
                notes,
                added_at,
                added_by
            FROM career_analysis_list
            ORDER BY added_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON tags
            if result.get('tags'):
                try:
                    result['tags'] = json.loads(result['tags'])
                except:
                    result['tags'] = []
            results.append(result)

        return {
            "status": "success",
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def add_to_career_list(assessment_id: str) -> Dict[str, Any]:
    """
    Add a career assessment to the list.

    Args:
        assessment_id: ID of the assessment to add

    Returns:
        API response dict
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get assessment details
        cursor.execute("""
            SELECT
                a.id as assessment_id,
                a.position_id,
                a.candidate_id,
                c.name as candidate_name,
                p.institution,
                p.department,
                p.position_title,
                p.hire_date,
                c.phd_institution,
                c.phd_year,
                a.overall_score,
                a.topic_alignment,
                a.publication_strength,
                a.network_overlap,
                a.methodology_match,
                c.publications_count,
                c.citations_count,
                a.confidence_overall
            FROM career_assessments a
            JOIN career_positions p ON a.position_id = p.id
            JOIN career_candidates c ON a.candidate_id = c.id
            WHERE a.id = ?
        """, (assessment_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return {
                "status": "error",
                "message": f"Assessment {assessment_id} not found"
            }

        # Check if already in list
        cursor.execute("SELECT id FROM career_analysis_list WHERE assessment_id = ?", (assessment_id,))
        if cursor.fetchone():
            conn.close()
            return {
                "status": "info",
                "message": "Assessment already in list"
            }

        # Insert into list
        list_id = f"list_{assessment_id[:12]}"
        cursor.execute("""
            INSERT INTO career_analysis_list (
                id, assessment_id, position_id, candidate_id,
                candidate_name, institution, department, position_title, hire_date,
                phd_institution, phd_year,
                overall_score, topic_alignment, publication_strength, network_overlap, methodology_match,
                publications_count, citations_count, confidence_score,
                tags, notes, added_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            list_id,
            row[0],  # assessment_id
            row[1],  # position_id
            row[2],  # candidate_id
            row[3],  # candidate_name
            row[4],  # institution
            row[5],  # department
            row[6],  # position_title
            row[7],  # hire_date
            row[8],  # phd_institution
            row[9],  # phd_year
            row[10], # overall_score
            row[11], # topic_alignment
            row[12], # publication_strength
            row[13], # network_overlap
            row[14], # methodology_match
            row[15], # publications_count
            row[16], # citations_count
            row[17], # confidence_overall
            json.dumps([]),  # tags
            "",  # notes
            "system"
        ))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": "Assessment added to Career Analysis list",
            "list_id": list_id
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def remove_from_career_list(list_id: str) -> Dict[str, Any]:
    """
    Remove an item from the career analysis list.

    Args:
        list_id: ID of the list item to remove

    Returns:
        API response dict
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM career_analysis_list WHERE id = ?", (list_id,))
        affected = cursor.rowcount

        conn.commit()
        conn.close()

        if affected > 0:
            return {
                "status": "success",
                "message": "Removed from Career Analysis list"
            }
        else:
            return {
                "status": "error",
                "message": "Item not found"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def update_list_item_notes(list_id: str, notes: str) -> Dict[str, Any]:
    """
    Update notes for a list item.

    Args:
        list_id: ID of the list item
        notes: New notes text

    Returns:
        API response dict
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE career_analysis_list SET notes = ? WHERE id = ?",
            (notes, list_id)
        )
        affected = cursor.rowcount

        conn.commit()
        conn.close()

        if affected > 0:
            return {
                "status": "success",
                "message": "Notes updated"
            }
        else:
            return {
                "status": "error",
                "message": "Item not found"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
