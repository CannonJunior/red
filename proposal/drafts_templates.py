"""
proposal/drafts_templates.py — Built-in section tree templates for each
government proposal document type.

Each template is a list of dicts with these keys:
  section_number  str    e.g. "1", "1.1", "1.1.2"
  title           str    Section heading
  guidance        str    Instructions shown to the writer
  parent_number   str|None  section_number of the logical parent ("" = root)
  sort_order      int

Templates are consumed by apply_template(), which creates all sections in
the drafts DB under a given document_id.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from proposal.drafts_db import create_section

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

_TECHNICAL_VOLUME: List[Dict] = [
    {"section_number": "1", "title": "Executive Summary", "parent_number": None,
     "sort_order": 10, "guidance": (
         "Provide a compelling, concise overview (≤ 2 pages). Lead with your "
         "win theme. State your understanding of the problem, your solution, "
         "and why your team is uniquely qualified. This section must stand alone "
         "— evaluators often read it first and last."
     )},
    {"section_number": "2", "title": "Technical Approach", "parent_number": None,
     "sort_order": 20, "guidance": (
         "Describe the overall solution methodology. Reference Section L/M "
         "requirements explicitly. Each sub-section should map to an evaluation "
         "criterion."
     )},
    {"section_number": "2.1", "title": "Understanding of the Problem", "parent_number": "2",
     "sort_order": 10, "guidance": (
         "Demonstrate a thorough understanding of the Government's challenge. "
         "Avoid paraphrasing the SOW — show insight and nuance."
     )},
    {"section_number": "2.2", "title": "Technical Solution", "parent_number": "2",
     "sort_order": 20, "guidance": (
         "Detail the proposed technical approach. Include diagrams (described in "
         "text) showing architecture, data flows, or processes. Address risk "
         "areas proactively."
     )},
    {"section_number": "2.3", "title": "Innovation and Differentiation", "parent_number": "2",
     "sort_order": 30, "guidance": (
         "Highlight unique aspects of your approach. Quantify claims where "
         "possible (speed, cost, accuracy improvements)."
     )},
    {"section_number": "3", "title": "Management Approach", "parent_number": None,
     "sort_order": 30, "guidance": (
         "Describe how the project will be managed — leadership, reporting "
         "structure, communication cadence, and risk management."
     )},
    {"section_number": "3.1", "title": "Program Management Plan", "parent_number": "3",
     "sort_order": 10, "guidance": (
         "Include org chart, RACI matrix, and escalation paths. Reference "
         "your PM's credentials."
     )},
    {"section_number": "3.2", "title": "Risk Management", "parent_number": "3",
     "sort_order": 20, "guidance": (
         "Identify top 3–5 risks with probability/impact ratings and mitigations. "
         "Demonstrate awareness without alarming the evaluator."
     )},
    {"section_number": "3.3", "title": "Quality Assurance", "parent_number": "3",
     "sort_order": 30, "guidance": (
         "Describe QA/QC processes, inspection gates, and metrics."
     )},
    {"section_number": "4", "title": "Past Performance", "parent_number": None,
     "sort_order": 40, "guidance": (
         "Reference 3–5 relevant contracts. Use CPARS ratings where available. "
         "Directly map each reference to requirements in this RFP."
     )},
    {"section_number": "5", "title": "Key Personnel", "parent_number": None,
     "sort_order": 50, "guidance": (
         "Provide résumé summaries for all key personnel. Highlight "
         "certifications, clearances, and directly relevant experience."
     )},
]

_MANAGEMENT_VOLUME: List[Dict] = [
    {"section_number": "1", "title": "Management Philosophy", "parent_number": None,
     "sort_order": 10, "guidance": (
         "State your company's management approach and how it aligns with "
         "the Government's objectives for this contract."
     )},
    {"section_number": "2", "title": "Organizational Structure", "parent_number": None,
     "sort_order": 20, "guidance": (
         "Include org chart with reporting lines. Distinguish between prime, "
         "subcontractor, and Government interfaces."
     )},
    {"section_number": "3", "title": "Staffing Plan", "parent_number": None,
     "sort_order": 30, "guidance": (
         "Describe recruiting, retention, and backfill strategies. Include a "
         "staffing matrix mapping labor categories to tasks."
     )},
    {"section_number": "4", "title": "Subcontracting Plan", "parent_number": None,
     "sort_order": 40, "guidance": (
         "Detail small business utilization goals, partner roles, and oversight "
         "mechanisms. Required if >$750K and not small business set-aside."
     )},
    {"section_number": "5", "title": "Transition Plan", "parent_number": None,
     "sort_order": 50, "guidance": (
         "Describe how you will assume/transition work with zero disruption. "
         "Include a 90-day onboarding timeline."
     )},
]

_COST_VOLUME: List[Dict] = [
    {"section_number": "1", "title": "Cost Summary", "parent_number": None,
     "sort_order": 10, "guidance": (
         "Provide a top-level cost table by CLIN/task order. Include base "
         "period + all option years. Must reconcile to supporting detail."
     )},
    {"section_number": "2", "title": "Labor Cost Detail", "parent_number": None,
     "sort_order": 20, "guidance": (
         "Break down labor by labor category, hours, and fully-burdened rates. "
         "Justify rates with market data or existing BOEs."
     )},
    {"section_number": "3", "title": "Other Direct Costs (ODC)", "parent_number": None,
     "sort_order": 30, "guidance": (
         "Itemize travel, materials, subcontracts, and other ODCs. Provide "
         "assumptions and supporting quotes for items >$25K."
     )},
    {"section_number": "4", "title": "Indirect Rates", "parent_number": None,
     "sort_order": 40, "guidance": (
         "State overhead, G&A, and fringe rates. Reference DCAA audit, forward "
         "pricing rate agreement (FPRA), or proposed rates with basis."
     )},
    {"section_number": "5", "title": "Cost Realism Narrative", "parent_number": None,
     "sort_order": 50, "guidance": (
         "Explain your assumptions. Acknowledge risks and show contingency. "
         "Demonstrate value without appearing low-balling."
     )},
    {"section_number": "6", "title": "Fee/Profit Justification", "parent_number": None,
     "sort_order": 60, "guidance": (
         "Justify fee rate using weighted guidelines (FAR 15.404-4). Address "
         "contractor risk, capital investment, and performance."
     )},
]

_PAST_PERFORMANCE: List[Dict] = [
    {"section_number": "1", "title": "Past Performance Summary", "parent_number": None,
     "sort_order": 10, "guidance": (
         "Summarize the relevance of your past performance portfolio to this "
         "requirement. Map experiences to evaluation criteria."
     )},
    {"section_number": "2", "title": "Reference 1", "parent_number": None,
     "sort_order": 20, "guidance": (
         "Contract Number, Agency, Period of Performance, Dollar Value, "
         "POC Name/Phone/Email, description of work and relevance. "
         "CPARS/PPIRS rating if available."
     )},
    {"section_number": "3", "title": "Reference 2", "parent_number": None,
     "sort_order": 30, "guidance": "Same structure as Reference 1."},
    {"section_number": "4", "title": "Reference 3", "parent_number": None,
     "sort_order": 40, "guidance": "Same structure as Reference 1."},
]

_SOW: List[Dict] = [
    {"section_number": "1", "title": "Scope of Work", "parent_number": None,
     "sort_order": 10, "guidance": (
         "Define the high-level purpose and boundaries of the work. Reference "
         "the PWS/SOO as applicable."
     )},
    {"section_number": "2", "title": "Tasks and Deliverables", "parent_number": None,
     "sort_order": 20, "guidance": (
         "List each task with a description, deliverable, due date, and "
         "acceptance criteria. Align to CDRL if applicable."
     )},
    {"section_number": "2.1", "title": "Task 1", "parent_number": "2",
     "sort_order": 10, "guidance": "Task description, inputs, outputs, acceptance criteria."},
    {"section_number": "2.2", "title": "Task 2", "parent_number": "2",
     "sort_order": 20, "guidance": "Task description, inputs, outputs, acceptance criteria."},
    {"section_number": "3", "title": "Government-Furnished Information / Equipment",
     "parent_number": None, "sort_order": 30, "guidance": (
         "List all GFI/GFE the Government will provide. Include expected "
         "delivery dates and POCs."
     )},
    {"section_number": "4", "title": "Applicable Documents", "parent_number": None,
     "sort_order": 40, "guidance": (
         "List all referenced standards, regulations, and documents "
         "(FAR clauses, MIL-STDs, etc.)."
     )},
    {"section_number": "5", "title": "Reporting Requirements", "parent_number": None,
     "sort_order": 50, "guidance": (
         "Describe status reporting cadence, format, and distribution list."
     )},
]

_PWS: List[Dict] = [
    {"section_number": "1", "title": "Purpose", "parent_number": None,
     "sort_order": 10, "guidance": (
         "State the mission need driving this requirement."
     )},
    {"section_number": "2", "title": "Scope", "parent_number": None,
     "sort_order": 20, "guidance": (
         "Define boundaries: what is/is not included."
     )},
    {"section_number": "3", "title": "Performance Requirements", "parent_number": None,
     "sort_order": 30, "guidance": (
         "State outcomes, not methods. Use SMART criteria. Map each requirement "
         "to an AQL (Acceptable Quality Level) in the QASP."
     )},
    {"section_number": "3.1", "title": "Required Outcomes", "parent_number": "3",
     "sort_order": 10, "guidance": "List measurable outcomes with performance standards."},
    {"section_number": "3.2", "title": "Quality Assurance Surveillance Plan (QASP)",
     "parent_number": "3", "sort_order": 20,
     "guidance": "Map each outcome to surveillance method and acceptable quality level."},
    {"section_number": "4", "title": "Place of Performance", "parent_number": None,
     "sort_order": 40, "guidance": "Specify location(s), facility security requirements."},
    {"section_number": "5", "title": "Period of Performance", "parent_number": None,
     "sort_order": 50, "guidance": "Base period + option periods with specific dates."},
]

_WBS: List[Dict] = [
    {"section_number": "1", "title": "Project", "parent_number": None,
     "sort_order": 10, "guidance": "Top-level WBS element — overall project name."},
    {"section_number": "1.1", "title": "Program Management", "parent_number": "1",
     "sort_order": 10, "guidance": (
         "Oversight, reporting, subcontractor management, risk management, "
         "quality assurance, and configuration management."
     )},
    {"section_number": "1.2", "title": "Systems Engineering", "parent_number": "1",
     "sort_order": 20, "guidance": (
         "Requirements analysis, architecture design, integration, and "
         "verification activities."
     )},
    {"section_number": "1.3", "title": "Development / Production", "parent_number": "1",
     "sort_order": 30, "guidance": (
         "Core technical work. Break down into sub-elements matching SOW tasks."
     )},
    {"section_number": "1.3.1", "title": "Task 1", "parent_number": "1.3",
     "sort_order": 10, "guidance": "Work packages for Task 1."},
    {"section_number": "1.3.2", "title": "Task 2", "parent_number": "1.3",
     "sort_order": 20, "guidance": "Work packages for Task 2."},
    {"section_number": "1.4", "title": "Test and Evaluation", "parent_number": "1",
     "sort_order": 40, "guidance": "Unit testing, integration testing, and acceptance testing."},
    {"section_number": "1.5", "title": "Logistics and Sustainment", "parent_number": "1",
     "sort_order": 50, "guidance": "Maintenance, training, and supply chain support."},
    {"section_number": "1.6", "title": "Data / CDRL", "parent_number": "1",
     "sort_order": 60, "guidance": "Data item deliverables and documentation."},
]

_CDRL: List[Dict] = [
    {"section_number": "1", "title": "CDRL Overview", "parent_number": None,
     "sort_order": 10, "guidance": (
         "Introduction to the Contract Data Requirements List. Reference "
         "the applicable DIDs (Data Item Descriptions)."
     )},
    {"section_number": "2", "title": "Data Item A001 — Program Management Plan",
     "parent_number": None, "sort_order": 20,
     "guidance": "DID reference, frequency, distribution, first submission date."},
    {"section_number": "3", "title": "Data Item A002 — Monthly Status Report",
     "parent_number": None, "sort_order": 30,
     "guidance": "DID reference, frequency, distribution, first submission date."},
    {"section_number": "4", "title": "Data Item A003 — Technical Report",
     "parent_number": None, "sort_order": 40,
     "guidance": "DID reference, frequency, distribution, first submission date."},
]

_COMPLIANCE_MATRIX: List[Dict] = [
    {"section_number": "1", "title": "Instructions to Offerors (Section L)",
     "parent_number": None, "sort_order": 10,
     "guidance": (
         "List each requirement from Section L with a mapping to the proposal "
         "section that addresses it and the compliance status."
     )},
    {"section_number": "2", "title": "Evaluation Criteria (Section M)",
     "parent_number": None, "sort_order": 20,
     "guidance": (
         "List each evaluation factor and sub-factor from Section M. Map to "
         "proposal sections and briefly note the win-theme addressed."
     )},
    {"section_number": "3", "title": "Statement of Work / PWS (Section C)",
     "parent_number": None, "sort_order": 30,
     "guidance": (
         "Map each SOW/PWS paragraph to the Technical Volume section that "
         "responds to it."
     )},
    {"section_number": "4", "title": "Compliance Summary", "parent_number": None,
     "sort_order": 40, "guidance": (
         "Executive summary: number of requirements, fully compliant, partially "
         "compliant, and any deviations with justification."
     )},
]

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, List[Dict]] = {
    "technical_volume": _TECHNICAL_VOLUME,
    "management_volume": _MANAGEMENT_VOLUME,
    "cost_volume": _COST_VOLUME,
    "past_performance": _PAST_PERFORMANCE,
    "sow": _SOW,
    "pws": _PWS,
    "wbs": _WBS,
    "cdrl": _CDRL,
    "compliance_matrix": _COMPLIANCE_MATRIX,
}

DOC_TYPE_LABELS: Dict[str, str] = {
    "technical_volume": "Technical Volume",
    "management_volume": "Management Volume",
    "cost_volume": "Cost Volume",
    "past_performance": "Past Performance",
    "sow": "Statement of Work (SOW)",
    "pws": "Performance Work Statement (PWS)",
    "wbs": "Work Breakdown Structure (WBS)",
    "cdrl": "Contract Data Requirements List (CDRL)",
    "compliance_matrix": "Compliance Matrix",
}


# ---------------------------------------------------------------------------
# Apply template
# ---------------------------------------------------------------------------

def apply_template(document_id: str, doc_type: str,
                   owner: str = "") -> List[Dict]:
    """
    Create all sections for a document from its built-in template.

    Args:
        document_id: The target proposal_documents.id.
        doc_type: Template key (e.g. 'technical_volume').
        owner: Default owner assigned to each section.

    Returns:
        list[dict]: The created section records (flat list in sort order).

    Raises:
        ValueError: If doc_type has no registered template.
    """
    template = TEMPLATES.get(doc_type)
    if template is None:
        raise ValueError(f"No template registered for doc_type '{doc_type}'. "
                         f"Valid types: {list(TEMPLATES)}")

    # Two-pass: first create all root sections (no parent), then children.
    # We need to map section_number → created section id for parent linking.
    id_by_number: Dict[str, str] = {}
    created: List[Dict] = []

    # Sort so parents always come before children (parents have shorter numbers)
    ordered = sorted(template, key=lambda s: (len(s["section_number"]), s["section_number"]))

    for spec in ordered:
        parent_num = spec.get("parent_number")
        parent_id: Optional[str] = id_by_number.get(parent_num) if parent_num else None
        section = create_section(
            document_id=document_id,
            title=spec["title"],
            parent_id=parent_id,
            section_number=spec["section_number"],
            guidance=spec.get("guidance", ""),
            owner=owner,
            sort_order=spec.get("sort_order", 0),
        )
        if section:
            id_by_number[spec["section_number"]] = section["id"]
            created.append(section)

    return created


def list_doc_types() -> List[Dict[str, str]]:
    """
    Return all available document types with their display labels.

    Returns:
        list[dict]: Each dict has 'key' and 'label'.
    """
    return [{"key": k, "label": v} for k, v in DOC_TYPE_LABELS.items()]
