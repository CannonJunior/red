---
name: bid-no-bid
description: "Shipley-based Bid/No-Bid assessment toolkit for government proposals. When Claude needs to: (1) Conduct a structured Go/No-Go decision analysis for a proposal opportunity, (2) Score weighted criteria (customer knowledge, competitive position, technical capability, team availability, etc.), (3) Generate a Bid/No-Bid decision slide (PPTX) for leadership review, (4) Record the formal bid decision with rationale in the proposals database, (5) Advance the proposal pipeline stage after a decision is made. Use AFTER opportunity-curator identifies a viable pursuit."
---

# Bid/No-Bid Assessment

## Overview

This skill implements the **Shipley Go/No-Go methodology** — the industry-standard approach for making data-driven bid decisions. It prevents wasted proposal effort on low-probability pursuits.

**Key Capabilities**:
- Conduct structured 8-factor weighted scoring interview
- Calculate Probability of Win (Pwin) estimate
- Generate Bid/No-Bid decision slide deck (PPTX)
- Record formal decision with rationale and decision-maker
- Advance proposal to `active` or `no_bid` pipeline stage
- Sync decision to Unanet CRM (via crm-sync skill)

## Workflow Position

```
[opportunity-curator] → BID/NO-BID → [proposal-setup (if BID)]
                                    → [hotwash (if NO-BID)]
```

## Scoring Criteria (Shipley 8-Factor Model)

Each criterion scored 1-10 with configurable weights:

| # | Criterion | Weight | Description |
|---|-----------|--------|-------------|
| 1 | Customer Knowledge | 1.5x | Existing relationship, prior interactions, access |
| 2 | Competitive Position | 1.5x | Win probability vs. known competitors |
| 3 | Incumbent Advantage | 1.25x | Prior work with this customer on this effort |
| 4 | Technical Capability | 1.5x | Team can deliver the required scope |
| 5 | Past Performance | 1.25x | Directly relevant, citable contracts |
| 6 | Team Availability | 1.0x | Key personnel available for PoP start date |
| 7 | Price Competitiveness | 1.25x | Can we hit Price-to-Win and still profit? |
| 8 | Risk Assessment | 1.0x | Technical, programmatic, and financial risks |

**Score interpretation (weighted average × 10)**:
- ≥70: **BID** — Strong pursuit, commit resources
- 50-69: **CONDITIONAL** — Bid if key risks resolved or teaming found
- <50: **NO-BID** — Document rationale, watch for recompete

## Quick Start

### Interactive Assessment

```
User: "Run a bid/no-bid for FA8612-26-R-0001"

Claude will:
1. Load the proposal from the database
2. Ask for scores on each criterion (or accept Claude's analysis)
3. Calculate weighted score
4. Generate recommendation with rationale
5. Ask for decision-maker confirmation
6. Record decision and update pipeline stage
7. Offer to generate the B/NB slide deck
```

### Generate B/NB Slide

```
User: "Generate the bid/no-bid slide for FA8612-26-R-0001"

Claude will:
1. Load existing B/NB assessment from database
2. Create PPTX using pptx skill
3. Save to outputs/proposal/{solicitation}/bid-no-bid/
4. Return file path and SharePoint upload option
```

## Output Format

### Database Record
```json
{
  "proposal_id": "uuid",
  "weighted_score": 74.5,
  "recommendation": "bid",
  "final_decision": "bid",
  "decision_made_by": "Jane Smith",
  "decision_date": "2026-03-28",
  "criteria": [
    {"name": "Customer Knowledge", "score": 8, "weight": 1.5, "notes": "Multiple meetings with PM"},
    ...
  ],
  "win_themes": ["AI/ML expertise", "SDVOSB set-aside", "incumbent subcontractor"],
  "discriminators": ["Clearance holders on staff", "Existing infrastructure"],
  "risks": ["Key personnel availability Q3", "Tight 60-day proposal schedule"],
  "recommendation_rationale": "Score 74.5/100. Strong customer relationship and competitive SDVOSB position..."
}
```

### Generated Slide Deck
```
FA8612-26-R-0001_bid_no_bid_2026-03-28.pptx
├── Slide 1: Opportunity Summary (title, agency, value, due date)
├── Slide 2: Scoring Matrix (visual scorecard with weights)
├── Slide 3: Pwin Analysis (competitive landscape, ghost analysis)
├── Slide 4: Win Themes & Discriminators
├── Slide 5: Risks & Mitigations
└── Slide 6: DECISION (BID/NO-BID/CONDITIONAL with rationale)
```

## File Naming Convention

```
outputs/proposal/{solicitation}/{solicitation}_bid_no_bid_{YYYY-MM-DD}.pptx
outputs/proposal/{solicitation}/{solicitation}_bid_no_bid_{YYYY-MM-DD}.xlsx
```

## Implementation

This skill invokes `proposal/bid_no_bid.py` and `proposal/bid_no_bid_slide.py` (Phase 1):

```python
from proposal.bid_no_bid import run_assessment, get_recommendation
from proposal.database import save_bid_no_bid, update_proposal
```

## Improvement Loop

After each proposal outcome (via hotwash skill):
- Compare predicted Pwin vs. actual outcome
- Adjust criterion weights for this customer/agency type
- Update scoring model for similar future opportunities
