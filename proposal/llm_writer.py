"""
proposal/llm_writer.py — LLM-assisted proposal writing actions.

Five action types are supported:
  plan              Build an outline / writing plan for a section
  draft             Generate an initial draft for a section
  improve           Rewrite / improve existing section content
  respond_comments  Address open comments and revise section content
  compliance_check  Check the section against compliance criteria

All functions take a ProposalWriteContext (assembled by the caller from
the DB) and return a plain string — the LLM's text output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from config.model_config import get_model, ModelTier
    _DEFAULT_LOCAL_MODEL = get_model(ModelTier.LOCAL)
except Exception:
    _DEFAULT_LOCAL_MODEL = "qwen2.5:3b"

# ---------------------------------------------------------------------------
# Context dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProposalWriteContext:
    """
    Aggregates all context needed by prompt builders.

    Attributes:
        proposal_title: Name of the proposal / opportunity.
        doc_type: Document type slug (e.g. 'technical_volume').
        section_title: Title of the section being worked on.
        section_number: e.g. "2.1"
        current_content: Existing draft text (may be empty).
        guidance: Template guidance text for this section.
        win_themes: List of win-theme strings for the proposal.
        open_comments: List of comment dicts with 'author' and 'content'.
        compliance_requirements: List of requirement strings for
                                  compliance-check action.
        word_limit: Optional word limit for the section.
        model: Ollama model name to use (e.g. 'llama3').
    """
    proposal_title: str
    doc_type: str
    section_title: str
    section_number: str = ""
    current_content: str = ""
    guidance: str = ""
    win_themes: List[str] = field(default_factory=list)
    open_comments: List[Dict] = field(default_factory=list)
    compliance_requirements: List[str] = field(default_factory=list)
    word_limit: Optional[int] = None
    model: str = field(default_factory=lambda: _DEFAULT_LOCAL_MODEL)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _base_context(ctx: ProposalWriteContext) -> str:
    """Return a shared preamble included in every prompt."""
    parts = [
        f"You are an expert government proposal writer using the Shipley methodology.",
        f"Proposal: {ctx.proposal_title}",
        f"Document type: {ctx.doc_type.replace('_', ' ').title()}",
        f"Section {ctx.section_number}: {ctx.section_title}",
    ]
    if ctx.win_themes:
        themes = "; ".join(ctx.win_themes)
        parts.append(f"Win themes: {themes}")
    if ctx.guidance:
        parts.append(f"Section guidance: {ctx.guidance}")
    if ctx.word_limit:
        parts.append(f"Target word limit: ~{ctx.word_limit} words")
    return "\n".join(parts)


def _build_plan_prompt(ctx: ProposalWriteContext) -> str:
    """
    Build prompt to produce a writing plan / outline for the section.

    Args:
        ctx: Proposal writing context.

    Returns:
        str: Full prompt string.
    """
    return f"""{_base_context(ctx)}

Task: Create a detailed writing plan (outline) for this section.

Return a numbered outline with:
- Key points to cover in logical order
- Sub-points for complex topics
- Win-theme touchpoints to include
- Recommended evidence or examples to include

Do NOT write the actual prose — only the plan.
"""


def _build_draft_prompt(ctx: ProposalWriteContext) -> str:
    """
    Build prompt to generate an initial draft of the section.

    Args:
        ctx: Proposal writing context.

    Returns:
        str: Full prompt string.
    """
    existing = ""
    if ctx.current_content.strip():
        existing = f"\nExisting notes / outline to expand:\n{ctx.current_content}\n"
    return f"""{_base_context(ctx)}
{existing}
Task: Write a complete, compelling proposal section using the guidance above.

Requirements:
- Professional government proposal style (active voice, specific, quantified)
- Weave in the win themes naturally
- Address evaluation criteria implied by the section guidance
- Use clear headings within the section if appropriate
- Comply with the word limit if specified

Write the full section prose now.
"""


def _build_improve_prompt(ctx: ProposalWriteContext) -> str:
    """
    Build prompt to improve / rewrite existing section content.

    Args:
        ctx: Proposal writing context.

    Returns:
        str: Full prompt string.
    """
    if not ctx.current_content.strip():
        return _build_draft_prompt(ctx)
    return f"""{_base_context(ctx)}

Current draft:
\"\"\"
{ctx.current_content}
\"\"\"

Task: Improve this proposal section. Focus on:
1. Strengthening win themes and discriminators
2. Making claims more specific and quantified
3. Improving flow and readability
4. Ensuring Section L/M compliance
5. Eliminating passive voice and jargon

Return only the improved text (no explanation).
"""


def _build_respond_comments_prompt(ctx: ProposalWriteContext) -> str:
    """
    Build prompt to address reviewer comments and revise the section.

    Args:
        ctx: Proposal writing context.

    Returns:
        str: Full prompt string.
    """
    if not ctx.open_comments:
        return _build_improve_prompt(ctx)

    comments_text = "\n".join(
        f"  [{i+1}] {c.get('author', 'Reviewer')}: {c.get('content', '')}"
        for i, c in enumerate(ctx.open_comments)
    )
    return f"""{_base_context(ctx)}

Current draft:
\"\"\"
{ctx.current_content}
\"\"\"

Open reviewer comments:
{comments_text}

Task: Revise the section to address ALL reviewer comments above.
- Incorporate suggestions that strengthen the proposal
- If a comment is contradictory or unclear, use best judgment aligned with win themes
- Return only the revised section text, no explanation or comment attributions.
"""


def _build_compliance_check_prompt(ctx: ProposalWriteContext) -> str:
    """
    Build prompt to check section content against compliance requirements.

    Args:
        ctx: Proposal writing context.

    Returns:
        str: Full prompt string.
    """
    reqs = "\n".join(f"  - {r}" for r in ctx.compliance_requirements) \
           if ctx.compliance_requirements else "  (No specific requirements provided)"
    draft = ctx.current_content.strip() or "(Section not yet written)"
    return f"""{_base_context(ctx)}

Compliance requirements for this section:
{reqs}

Current draft:
\"\"\"
{draft}
\"\"\"

Task: Perform a compliance check. For each requirement:
1. State whether the current draft addresses it (Compliant / Partial / Missing)
2. If Partial or Missing, provide a specific suggestion for what to add

Return a structured compliance report, one row per requirement.
"""


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_PROMPT_BUILDERS = {
    "plan": _build_plan_prompt,
    "draft": _build_draft_prompt,
    "improve": _build_improve_prompt,
    "respond_comments": _build_respond_comments_prompt,
    "compliance_check": _build_compliance_check_prompt,
}


def run_llm_action(action: str, ctx: ProposalWriteContext) -> str:
    """
    Execute an LLM writing action and return the generated text.

    Args:
        action: One of 'plan', 'draft', 'improve', 'respond_comments',
                'compliance_check'.
        ctx: Assembled context for the section.

    Returns:
        str: LLM-generated text, or an error message string.

    Raises:
        ValueError: If action is not recognised.
    """
    builder = _PROMPT_BUILDERS.get(action)
    if builder is None:
        raise ValueError(f"Unknown LLM action '{action}'. "
                         f"Valid: {list(_PROMPT_BUILDERS)}")

    prompt = builder(ctx)

    try:
        from ollama_config import ollama_config  # type: ignore[import]
        result = ollama_config.generate_response(ctx.model, prompt)
        if result.get("success"):
            return result["data"].get("response", "").strip()
        error = result.get("error", "Unknown error")
        logger.error("Ollama error during '%s': %s", action, error)
        return f"[LLM error: {error}]"
    except Exception as exc:
        logger.exception("Unexpected error calling Ollama for action '%s'", action)
        return f"[LLM error: {exc}]"


def list_actions() -> List[Dict[str, str]]:
    """
    Return metadata for all supported LLM actions.

    Returns:
        list[dict]: Each dict has 'key', 'label', 'description'.
    """
    return [
        {"key": "plan",             "label": "Plan",
         "description": "Generate a writing outline for this section"},
        {"key": "draft",            "label": "Draft",
         "description": "Write an initial draft based on guidance and notes"},
        {"key": "improve",          "label": "Improve",
         "description": "Rewrite and strengthen the current draft"},
        {"key": "respond_comments", "label": "Respond to Comments",
         "description": "Revise the draft to address all open reviewer comments"},
        {"key": "compliance_check", "label": "Compliance Check",
         "description": "Check the draft against stated requirements"},
    ]
