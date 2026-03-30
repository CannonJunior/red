"""
Proposal Folder Manager.

Creates and manages the standard local folder structure for an active proposal
under outputs/proposal/{solicitation}/.

Structure is defined as a config constant so it can be adjusted without
code changes (or overridden via PROPOSAL_FOLDER_CONFIG_FILE env var).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from proposal.models import Proposal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Folder structure config
# ---------------------------------------------------------------------------

# Reason: Config-driven structure so teams can extend without code changes
_DEFAULT_FOLDER_STRUCTURE: List[str] = [
    "00_rfp",
    "01_analysis/shredding",
    "02_bid_no_bid",
    "03_working/vol_1_technical",
    "03_working/vol_2_management",
    "03_working/vol_3_cost",
    "03_working/vol_4_past_performance",
    "04_reviews/pink_team",
    "04_reviews/red_team",
    "04_reviews/gold_team",
    "05_final/internal",
    "05_final/submission",
    "_admin",
]


def _load_folder_structure() -> List[str]:
    """
    Load folder structure from config file if set, else use defaults.

    Returns:
        List[str]: Relative folder paths to create under proposal root.
    """
    cfg_file = os.getenv("PROPOSAL_FOLDER_CONFIG_FILE", "")
    if cfg_file and Path(cfg_file).exists():
        with open(cfg_file) as f:
            data = json.load(f)
        return data.get("folders", _DEFAULT_FOLDER_STRUCTURE)
    return _DEFAULT_FOLDER_STRUCTURE


def _proposal_root(proposal: Proposal, base_dir: Optional[Path] = None) -> Path:
    """
    Derive the root output folder for a proposal.

    Args:
        proposal: Proposal model instance.
        base_dir: Override base directory (default: outputs/proposal/ in cwd).

    Returns:
        Path: Absolute path to the proposal root folder.
    """
    sol_id = (proposal.solicitation_number or proposal.id[:8]).replace("/", "-")
    if base_dir:
        return base_dir / sol_id
    return Path(os.getcwd()) / "outputs" / "proposal" / sol_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_proposal_folders(
    proposal: Proposal,
    base_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """
    Create the standard local folder structure for an active proposal.

    Idempotent — safe to call multiple times; existing folders are not modified.

    Args:
        proposal: Proposal model instance.
        base_dir: Override the base output directory.

    Returns:
        Dict[str, Path]: Map of folder key → absolute Path for each created folder.
            Also includes "root" key pointing to the proposal root.
    """
    root = _proposal_root(proposal, base_dir)
    folders = _load_folder_structure()

    created: Dict[str, Path] = {"root": root}
    root.mkdir(parents=True, exist_ok=True)

    for rel_path in folders:
        full = root / rel_path
        full.mkdir(parents=True, exist_ok=True)
        # Reason: Use the last path segment as a human-readable key
        key = rel_path.replace("/", "_").replace("\\", "_")
        created[key] = full
        logger.debug("Ensured folder: %s", full)

    logger.info(
        "Proposal folder structure ready for %s at %s (%d folders)",
        proposal.solicitation_number or proposal.id,
        root,
        len(folders),
    )
    return created


def get_folder(proposal: Proposal, key: str, base_dir: Optional[Path] = None) -> Path:
    """
    Get the path to a specific named folder within the proposal structure.

    Args:
        proposal: Proposal model instance.
        key: Folder key as it appears in _DEFAULT_FOLDER_STRUCTURE
             (e.g., "02_bid_no_bid", "03_working/vol_1_technical").
        base_dir: Override base directory.

    Returns:
        Path: Absolute path to the folder (may not exist yet).
    """
    root = _proposal_root(proposal, base_dir)
    return root / key


def place_file(
    proposal: Proposal,
    folder_key: str,
    filename: str,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Return the target path to place a file in a proposal folder, creating it if needed.

    Args:
        proposal: Proposal model instance.
        folder_key: Relative folder path within the proposal (e.g., "02_bid_no_bid").
        filename: Filename (e.g., "FA8612-26-R-0001_bid_no_bid_2026-03-28.pptx").
        base_dir: Override base directory.

    Returns:
        Path: Full target path for the file.
    """
    folder = get_folder(proposal, folder_key, base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / filename


def write_readme(proposal: Proposal, base_dir: Optional[Path] = None) -> Path:
    """
    Write a README.txt to the proposal root folder summarizing key metadata.

    Args:
        proposal: Proposal model instance.
        base_dir: Override base directory.

    Returns:
        Path: Path to the written README.txt.
    """
    root = _proposal_root(proposal, base_dir)
    root.mkdir(parents=True, exist_ok=True)

    pwin_str = f"{int(proposal.pwin_score * 100)}%" if proposal.pwin_score is not None else "TBD"
    lines = [
        f"Solicitation:   {proposal.solicitation_number or 'TBD'}",
        f"Title:          {proposal.title}",
        f"Agency:         {proposal.agency or 'TBD'}",
        f"NAICS:          {proposal.naics_code or 'TBD'}",
        f"Set-Aside:      {(proposal.set_aside_type or 'unknown').upper().replace('_', ' ')}",
        f"Est. Value:     ${proposal.estimated_value:,.0f}" if proposal.estimated_value else "Est. Value:     TBD",
        f"Proposal Due:   {proposal.proposal_due_date or 'TBD'}",
        f"Capture Mgr:    {proposal.capture_manager or 'Unassigned'}",
        f"Proposal Mgr:   {proposal.proposal_manager or 'Unassigned'}",
        f"Pwin:           {pwin_str}",
        f"Stage:          {proposal.pipeline_stage.value}",
        f"CRM ID:         {proposal.crm_opportunity_id or 'Not synced'}",
        "",
        "Folder Structure:",
    ]

    for folder in _load_folder_structure():
        lines.append(f"  {folder}/")

    content = "\n".join(lines) + "\n"
    readme_path = root / "README.txt"
    readme_path.write_text(content, encoding="utf-8")
    logger.info("Wrote proposal README: %s", readme_path)
    return readme_path


def folder_summary(proposal: Proposal, base_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Return a summary of the proposal folder structure with existence status.

    Args:
        proposal: Proposal model instance.
        base_dir: Override base directory.

    Returns:
        Dict[str, str]: Map of folder path → "exists" | "missing".
    """
    root = _proposal_root(proposal, base_dir)
    result: Dict[str, str] = {"root": "exists" if root.exists() else "missing"}
    for rel_path in _load_folder_structure():
        full = root / rel_path
        result[rel_path] = "exists" if full.exists() else "missing"
    return result
